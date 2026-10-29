# src/bootstrap/di.py
from dependency_injector import containers, providers
from src.core.application.ports.media_port import MediaProcessorPort
from src.core.domain.entities.lina import Lina
from src.core.domain.entities.lina_memory import LinaMemory
from src.core.domain.entities.user import User
from src.core.domain.value_objects.personality_trait import (
    PersonalityTrait,
    TraitType,
)
from src.core.domain.value_objects.principle import (
    Principle,
    PrincipleCategory,
    PrincipleSource,
)
from src.core.domain.value_objects.settings import Settings

from src.core.application.ports.command_bus import CommandBusPort
from src.core.application.ports.repositories import (
    SettingsRepository,
    LinaRepository,
    SessionRepositoryProt,
    LinaMemoryRepositoryPort,
    UserRepositoryPort,
)
from src.core.application.ports.llm_port import LLMPort

# --- Subsystems ---
from src.core.application.subsystems.memory.engine import MemoryEngine
from src.core.application.subsystems.emotion.engine import EmotionEngine
from src.core.application.subsystems.mood.engine import MoodEngine
from src.core.application.subsystems.tools.engine import ToolEngine
from src.core.application.subsystems.autonomy.engine import AutonomyEngine
from src.core.application.subsystems.tools.parser import ToolCallParser

# --- Orchestration ---
from src.core.application.orchestration.pipeline import Pipeline
from src.core.application.orchestration.chat_orchestration import ChatOrchestration
from src.core.application.orchestration.prompting.builder import PromptBuilder
from src.core.application.orchestration.autonomy_orchestration import (
    AutonomyOrchestration,
)

# --- Handlers ---
from src.core.application.handlers.chat_handler import SendMessageHandler
from src.core.application.handlers.speech_handler import RecognizeSpeechHandler
from src.core.application.commands.speech_commands import RecognizeSpeechCommand
from src.core.infrastructure.providers.stt.local.vosk_recognize import VoskRecognizer
from src.core.application.handlers.settings_handler import (
    LoadSettingsHandler,
    UpdateSettingsHandler,
    GetPluginListHandler,
    TogglePluginHandler,
    ToolPermissionsHandler,
)
from src.core.application.handlers.system_handlers import (
    StartSystemHandler,
    StopSystemHandler,
)

# --- Infrastructure ---
from src.core.infrastructure.providers.command_bus import CommandBus
from src.core.infrastructure.providers.event_bus import EventBus
from src.core.infrastructure.services.media_processor import FileMediaProcessor


from src.core.infrastructure.repositories.file_emotion_history_repository import FileEmotionHistoryRepository
from src.core.infrastructure.repositories.file_settings_repository import FileSettingsRepository
from src.core.infrastructure.repositories.json_state_repositories import (
    JsonLinaRepository, JsonUserRepository,
)
from src.core.infrastructure.providers.embeddings import SentenceTransformerEmbeddings
from src.core.infrastructure.repositories.sqlite_memory_repository import SQLiteMemoryRepository
from src.core.infrastructure.repositories.sqlite_session_repository import SQLiteSessionRepository
from src.core.application.orchestration.runtime_gate import RuntimeGate
from src.core.domain.value_objects.behavior_policy import BehaviorPolicy
from local_paths import (BASE_DIR, LLM_MODEL, VOSK_MODEL, EMBEDDING_MODEL, MMPROJ)
from src.core.infrastructure.providers.llm.local.provider import LlamaCppProvider

# --- Tool registry (in-memory, пока без плагинов) ---
from src.core.infrastructure.services.tools.in_memory_tool_registry import InMemoryToolRegistry
from src.core.application.subsystems.tools.jobs import BackgroundJobs
from src.core.application.subsystems.tools.permissions import ToolPermissions
from src.core.infrastructure.services.tools.permission_store import FileToolPermissionStore
from src.core.infrastructure.services.tools.builtin import BUILTIN_TOOLS

# --- Commands ---
from src.core.application.commands.chat_commands import SendMessageCommand
from src.core.application.commands.settings_commands import (
    LoadSettingsCommand,
    UpdateSettingsCommand,
    GetPluginListCommand,
    TogglePluginCommand,
    SetToolPermissionsCommand,
    ResolveToolPermissionCommand,
)
from src.core.application.commands.system_commands import (
    StartSystemCommand,
    StopSystemCommand,
)

import logging

logger = logging.getLogger(__name__)


def _build_speech_recognizer(model_path):
    from pathlib import Path
    from local_paths import VOSK_MODEL
    path = Path(model_path) if model_path else VOSK_MODEL
    return VoskRecognizer(path if path.is_absolute() else BASE_DIR / path)


def _build_tool_registry(plugins_enabled=True) -> InMemoryToolRegistry:
    """Собирает реестр: регистрирует все built-in tools."""
    registry = InMemoryToolRegistry()
    for tool_class in BUILTIN_TOOLS:
        registry.register_builtin(tool_class)
    from src.core.infrastructure.services.tools.plugins import discover
    if plugins_enabled:
        discover(registry, BASE_DIR / "plugins", BASE_DIR / ".plugin-envs")
    return registry


class Container(containers.DeclarativeContainer):
    """Composition Root приложения."""

    # ============================================================
    # CONFIGURATION
    # ============================================================

    config = providers.Configuration()
    policy = providers.Singleton(lambda data: BehaviorPolicy.from_dict(data or {}), config.behavior)
    gate = providers.Singleton(RuntimeGate)

    # ============================================================
    # BUSES
    # ============================================================

    event_bus = providers.Singleton(EventBus)
    command_bus = providers.Singleton(CommandBus)

    # ============================================================
    # REPOSITORIES
    # ============================================================

    settings_repo = providers.Singleton(
        FileSettingsRepository, str(BASE_DIR / "data/settings.json")
    )
    lina_repo = providers.Singleton(
        JsonLinaRepository, str(BASE_DIR / "data/lina.json")
    )
    session_repo = providers.Singleton(
        SQLiteSessionRepository, str(BASE_DIR / "data/conversations.sqlite3"),
        str(BASE_DIR / "data/sessions")
    )
    user_repo = providers.Singleton(
        JsonUserRepository, str(BASE_DIR / "data/user.json")
    )
    emotion_history_repo = providers.Singleton(
        FileEmotionHistoryRepository, data_dir=str(BASE_DIR / "data/emotions")
    )

    # ============================================================
    # LLM
    # ============================================================

    speech_recognizer = providers.Singleton(_build_speech_recognizer, model_path=config.vosk_model_path)
    recognize_speech_handler = providers.Factory(
        RecognizeSpeechHandler, recognizer=speech_recognizer, event_bus=event_bus, gate=gate,
    )

    llm = providers.Singleton(
        LlamaCppProvider,
        model_path=config.llm.model_path,
        mmproj_path=config.llm.mmproj_path,
        n_ctx=config.llm.context_window,
        n_threads=config.llm.n_threads,
        n_gpu_layers=config.llm.n_gpu_layers,
        enable_thinking=True,
        flash_attn=config.llm.flash_attn,
        offload_kqv=True,
        economy_mode=config.economy_mode,
        embedding_dim=768,
        chat_handler=config.llm.chat_handler,
    )

    # ============================================================
    # MEMORY REPO (SQLite + dedicated sentence embeddings)
    # ============================================================

    embeddings = providers.Singleton(SentenceTransformerEmbeddings, model_path=config.embedding_model_path)
    memory_repo = providers.Singleton(
        SQLiteMemoryRepository,
        embeddings=embeddings,
        path=str(BASE_DIR / "data/memory.sqlite3"),
    )

    # ============================================================
    # TOOL REGISTRY (пока in-memory, потом — plugin)
    # ============================================================

    tool_registry = providers.Singleton(_build_tool_registry, plugins_enabled=config.plugins_enabled)
    from src.core.infrastructure.services.tools.plugin_catalog import FilePluginCatalog
    plugin_catalog = providers.Singleton(FilePluginCatalog, BASE_DIR / "plugins", BASE_DIR / ".plugin-envs")


    # ============================================================
    # SUBSYSTEM ENGINES
    # ============================================================
    
    autonomy_engine = providers.Singleton(
        AutonomyEngine,
        event_bus=event_bus,
    )

    memory_engine = providers.Singleton(
        MemoryEngine,
        memory_repo=memory_repo,
        event_bus=event_bus,
        policy=policy,
    )

    emotion_engine = providers.Singleton(
        EmotionEngine,
        event_bus=event_bus,
        history=emotion_history_repo,
    )

    mood_engine = providers.Singleton(
        MoodEngine,
        history=emotion_history_repo,
        event_bus=event_bus,
        window_days=3,
    )

    background_jobs = providers.Singleton(BackgroundJobs, event_bus=event_bus)
    tool_permission_store = providers.Singleton(FileToolPermissionStore, BASE_DIR / "data" / "tool_permissions.json")
    tool_permissions = providers.Singleton(ToolPermissions, store=tool_permission_store, event_bus=event_bus)

    tool_engine = providers.Singleton(
        ToolEngine,
        registry=tool_registry,
        event_bus=event_bus,
        jobs=background_jobs,
        permissions=tool_permissions,
    )

    # ============================================================
    # PROMPTS / PARSER
    # ============================================================

    prompt_builder = providers.Singleton(PromptBuilder, policy=policy)
    media_processor = providers.Singleton(FileMediaProcessor)
    tool_call_parser = providers.Singleton(ToolCallParser)

    # ============================================================
    # PIPELINE
    # ============================================================

    pipeline = providers.Singleton(
        Pipeline,
        memory=memory_engine,
        emotion=emotion_engine,
        mood=mood_engine,
        tools=tool_engine,
        llm=llm,
        prompts=prompt_builder,
        parser=tool_call_parser,
        event_bus=event_bus,
    )

    # ============================================================
    # ORCHESTRATION
    # ============================================================

    chat_orchestration = providers.Singleton(
        ChatOrchestration,
        pipeline=pipeline,
        users=user_repo,
        sessions=session_repo,
        lina_repo=lina_repo,
        memory_repo=memory_repo,
        media_processor=media_processor,  
        event_bus=event_bus,
        gate=gate,
    )
    
    autonomy_orchestration = providers.Singleton(
        AutonomyOrchestration,
        autonomy=autonomy_engine,
        memory=memory_engine,
        emotion=emotion_engine,
        mood=mood_engine,
        tools=tool_engine,
        llm=llm,
        prompts=prompt_builder,
        event_bus=event_bus,
        tick_interval_seconds=60.0,
        gate=gate,
        policy=policy,
        lina_repo=lina_repo,
        users=user_repo,
        sessions=session_repo,
        memory_repo=memory_repo,
    )

    # ============================================================
    # COMMAND HANDLERS
    # ============================================================

    send_message_handler = providers.Factory(
        SendMessageHandler,
        orchestration=chat_orchestration,
    )

    load_settings_handler = providers.Factory(
        LoadSettingsHandler,
        settings_repo=settings_repo,
        event_bus=event_bus,
    )
    update_settings_handler = providers.Factory(
        UpdateSettingsHandler,
        settings_repo=settings_repo,
        event_bus=event_bus,
    )
    get_plugin_list_handler = providers.Factory(
        GetPluginListHandler,
        plugin_repo=plugin_catalog,
        event_bus=event_bus,
        permissions=tool_permissions,
    )
    toggle_plugin_handler = providers.Factory(
        TogglePluginHandler,
        plugin_repo=plugin_catalog,
        event_bus=event_bus,
        permissions=tool_permissions,
    )
    tool_permissions_handler = providers.Factory(
        ToolPermissionsHandler, plugin_repo=plugin_catalog, permissions=tool_permissions, event_bus=event_bus,
    )
    start_system_handler = providers.Factory(
        StartSystemHandler,
        settings_repo=settings_repo,
        event_bus=event_bus,
    )
    stop_system_handler = providers.Factory(
        StopSystemHandler,
        event_bus=event_bus,
    )
    
# src/bootstrap/di.py
# ... (импорты как были)
# ... (Container как был)

class ApplicationContainer:
    """
    Runtime-обёртка над DeclarativeContainer.
    Отвечает за lifecycle и регистрацию handlers.
    """

    def __init__(self):
        self.container = Container()
        self._settings: Settings | None = None
        self._handlers_registered = False

    # ============================================================
    # SETTINGS
    # ============================================================

    def set_settings(self, settings: Settings) -> None:
        cur = self._settings.to_dict() if self._settings else None
        new = settings.to_dict()

        logger.info(
            f"[Container] set_settings compare: "
            f"cur.on_gpu={cur.get('on_gpu') if cur else None!r}, "
            f"new.on_gpu={new.get('on_gpu')!r}, "
            f"equal={cur == new if cur else False}"
        )

        if cur is not None and cur == new:
            logger.debug("[Container] set_settings: no changes, skipping reset")
            return

        logger.info(f"[Container] set_settings: applying, on_gpu={settings.on_gpu}")

        self._settings = settings

        self.container.config.from_dict({
            "embedding_model_path": settings.embedding_model_path,
            "vosk_model_path": settings.vosk_model_path,
            "economy_mode": bool(settings.on_economy),
            "behavior": new["behavior"],
            "plugins_enabled": settings.on_plugins,
            "version": settings.version,
            "username": settings.username,
            "language": settings.language,
            "on_gpu": bool(settings.on_gpu),
            "llm": {
                "model_path": (settings.llm.model_path or str(LLM_MODEL)) if settings.llm else str(LLM_MODEL),
                "mmproj_path": (settings.llm.mmproj_path or str(MMPROJ)) if settings.llm else str(MMPROJ),
                "context_window": (settings.llm.context_window or 4096) if settings.llm else 4096,
                "n_threads": (settings.llm.n_threads or 4) if settings.llm else 4,
                "n_gpu_layers": -1 if settings.on_gpu else 0,
                "flash_attn": settings.llm.flash_attn if settings.llm else True,
                "chat_handler": settings.llm.chat_handler if settings.llm else "gemma4",
            },
        })

        self.container.llm.reset()
        self.container.speech_recognizer.reset()
        self._handlers_registered = False
        self.container.tool_registry.reset()
        self.container.tool_engine.reset()
        self.container.embeddings.reset()
        self.container.memory_repo.reset()
        for provider in (self.container.policy, self.container.memory_engine,
                         self.container.prompt_builder, self.container.pipeline,
                         self.container.chat_orchestration, self.container.autonomy_orchestration):
            provider.reset()

    def get_settings(self) -> Settings:
        if self._settings is None:
            raise RuntimeError("Settings are not loaded.")
        return self._settings

    # ============================================================
    # COMMAND BUS
    # ============================================================

    def get_command_bus(self) -> CommandBusPort:
        bus: CommandBusPort = self.container.command_bus()
        if not self._handlers_registered:
            self._register_handlers(bus)
        return bus

    def _register_handlers(self, bus: CommandBusPort) -> None:
        """Регистрация всех application command handlers."""
        bus.register(RecognizeSpeechCommand, self.container.recognize_speech_handler())
        bus.register(SetToolPermissionsCommand, self.container.tool_permissions_handler())
        bus.register(ResolveToolPermissionCommand, self.container.tool_permissions_handler())

        bus.register(
            SendMessageCommand,
            self.container.send_message_handler(),
        )

        bus.register(
            LoadSettingsCommand,
            self.container.load_settings_handler(),
        )
        bus.register(
            UpdateSettingsCommand,
            self.container.update_settings_handler(),
        )
        bus.register(
            GetPluginListCommand,
            self.container.get_plugin_list_handler(),
        )
        bus.register(
            TogglePluginCommand,
            self.container.toggle_plugin_handler(),
        )

        bus.register(
            StartSystemCommand,
            self.container.start_system_handler(),
        )
        bus.register(
            StopSystemCommand,
            self.container.stop_system_handler(),
        )

        self._handlers_registered = True

    # ============================================================
    # RESET / LIFECYCLE
    # ============================================================

    async def reset(self) -> None:
        """Полное освобождение runtime-зависимостей."""
        logger.info("[Container] Full reset")
        try:
            await self.container.speech_recognizer().close()
        except Exception:
            logger.exception("Error closing speech recognizer")
        self.container.speech_recognizer.reset()
        self.container.tool_permissions().cancel_pending()
        await self.container.background_jobs().close()
        self.container.background_jobs.reset()
        self.container.tool_engine.reset()

        llm: LLMPort | None = None
        try:
            llm = self.container.llm()
        except Exception:
            pass

        if llm is not None and hasattr(llm, "close"):
            try:
                result = llm.close()
                if hasattr(result, "__await__"):
                    await result
            except Exception:
                logger.exception("Error closing LLM")

        try:
            await self.container.embeddings().close()
        except Exception:
            logger.exception("Error closing embeddings")
            
        for provider in (self.container.llm, self.container.pipeline,
                         self.container.chat_orchestration,
                         self.container.autonomy_orchestration):
            provider.reset()
        self._handlers_registered = False

        import gc
        gc.collect()

    # ============================================================
    # LINA BOOTSTRAP
    # ============================================================

    async def ensure_lina(self) -> Lina:
        await self.container.memory_repo().record_core(self.container.policy())
        lina = await self.container.lina_repo().get()
        if lina is not None:
            memory = await self.container.memory_repo().get_by_lina(lina.id)
            if memory is not None:
                lina._memory = memory
            return lina

        from uuid import uuid4
        lina_id = uuid4()
        memory = LinaMemory(lina_id=lina_id)

        lina = Lina(
            memory=memory,
            personality={
                TraitType.CURIOSITY: PersonalityTrait(TraitType.CURIOSITY, 0.85),
                TraitType.PLAYFULNESS: PersonalityTrait(TraitType.PLAYFULNESS, 0.70),
                TraitType.EMPATHY: PersonalityTrait(TraitType.EMPATHY, 0.80),
                TraitType.EXTRAVERSION: PersonalityTrait(TraitType.EXTRAVERSION, 0.60),
                TraitType.OPENNESS: PersonalityTrait(TraitType.OPENNESS, 0.75),
                TraitType.CONSCIENTIOUSNESS: PersonalityTrait(TraitType.CONSCIENTIOUSNESS, 0.50),
                TraitType.NEUROTICISM: PersonalityTrait(TraitType.NEUROTICISM, 0.30),
            },
            principles=[
                Principle.create(
                    "Мне не нравится, когда пользователь грубит или обижает меня",
                    PrincipleCategory.BOUNDARY,
                    strength=0.9,
                    source=PrincipleSource.DEFAULT,
                ),
                Principle.create(
                    "Я люблю мечтать и обсуждать истории",
                    PrincipleCategory.PREFERENCE,
                    strength=0.7,
                    source=PrincipleSource.DEFAULT,
                ),
                Principle.create(
                    "Я ценю, когда пользователь проводит со мной время",
                    PrincipleCategory.VALUE,
                    strength=0.7,
                    source=PrincipleSource.DEFAULT,
                ),
            ],
            name="Lina",
        )
        lina.id = lina_id

        await self.container.lina_repo().save(lina)
        await self.container.memory_repo().save(memory)
        return lina

    async def ensure_user(self) -> User:
        settings = self.get_settings()
        user = await self.container.user_repo().get_default()
        if user is not None:
            user.name = settings.username
            user.preferred_language = settings.language
            await self.container.user_repo().save(user)
            return user
        user = User(
            name=settings.username,
            preferred_language=settings.language,
        )
        await self.container.user_repo().save(user)
        return user

    async def ensure_session(self, user_id):
        return await self.container.session_repo().ensure_for_user(user_id)

    # ============================================================
    # COMPATIBILITY HELPERS
    # ============================================================

    def get_settings_repo(self) -> SettingsRepository:
        return self.container.settings_repo()

    def get_lina_repo(self) -> LinaRepository:
        return self.container.lina_repo()

    def get_session_repo(self) -> SessionRepositoryProt:
        return self.container.session_repo()

    def get_user_repo(self) -> UserRepositoryPort:
        return self.container.user_repo()

    def get_memory_repo(self) -> LinaMemoryRepositoryPort:
        return self.container.memory_repo()

    def get_llm_client(self) -> LLMPort:
        return self.container.llm()

    def get_event_bus(self) -> EventBus:
        return self.container.event_bus()
