from src.core.application.ports.command_bus import CommandHandlerPort
from src.core.application.ports.repositories import SettingsRepository
from src.core.application.ports.plugin_catalog import PluginCatalogPort
from src.core.application.ports.event_port import EventBusPort as EventBus
from src.core.application.commands.settings_commands import *
from src.core.domain.events.settings_events import SettingsChanged, SettingsLoaded
from src.core.domain.events.plugin_events import PluginListReceived, PluginEnabled, PluginDisabled
from src.core.domain.value_objects.settings import Settings
from src.core.utils.logger import logger
logger = logger.get(__name__)


class LoadSettingsHandler(CommandHandlerPort):
    def __init__(self, settings_repo: SettingsRepository, event_bus: EventBus):
        self._settings_repo = settings_repo
        self._event_bus = event_bus

    async def handle(self, command: LoadSettingsCommand) -> None:
        settings = await self._settings_repo.get()
        if not settings:
            settings = Settings.default()
            await self._settings_repo.save(settings)

        await self._event_bus.publish(SettingsLoaded(
            settings=settings.to_dict(),
            source="file",
        ))


class UpdateSettingsHandler(CommandHandlerPort):
    def __init__(self, settings_repo: SettingsRepository, event_bus: EventBus):
        self._settings_repo = settings_repo
        self._event_bus = event_bus

    async def handle(self, command: UpdateSettingsCommand) -> None:
        current = await self._settings_repo.get() or Settings.default()

        old_data = current.to_dict()
        if old_data.get(command.field) == command.value:
            return

        new_data = dict(old_data)
        new_data[command.field] = command.value
        new_settings = Settings.from_dict(new_data)

        await self._settings_repo.save(new_settings)
        await self._event_bus.publish(SettingsChanged(
            old_settings=old_data,
            new_settings=new_settings.to_dict(),
            changed_fields=[command.field],
        ))


async def plugin_list(plugin_repo, permissions):
    plugins = await plugin_repo.list_plugins()
    if permissions is not None:
        for plugin in plugins:
            for spec in plugin.get("tool_specs", []):
                spec["granted_permissions"] = permissions.granted(spec["name"])
    return plugins


class GetPluginListHandler(CommandHandlerPort):
    def __init__(self, plugin_repo: PluginCatalogPort, event_bus: EventBus, permissions=None):
        self._plugin_repo = plugin_repo
        self._event_bus = event_bus
        self._permissions = permissions

    async def handle(self, command: GetPluginListCommand) -> None:
        await self._event_bus.publish(PluginListReceived(plugins=await plugin_list(self._plugin_repo, self._permissions)))


class TogglePluginHandler(CommandHandlerPort):
    def __init__(self, plugin_repo: PluginCatalogPort, event_bus: EventBus, permissions=None):
        self._plugin_repo = plugin_repo
        self._event_bus = event_bus
        self._permissions = permissions

    async def handle(self, command: TogglePluginCommand) -> None:
        await self._plugin_repo.set_enabled(command.plugin_name, command.enabled)
        await self._event_bus.publish(PluginListReceived(plugins=await plugin_list(self._plugin_repo, self._permissions)))


class ToolPermissionsHandler(CommandHandlerPort):
    def __init__(self, plugin_repo, permissions, event_bus):
        self._plugins, self._permissions, self._bus = plugin_repo, permissions, event_bus

    async def handle(self, command):
        if isinstance(command, SetToolPermissionsCommand):
            if not isinstance(command.permissions, list) or not all(isinstance(p, str) for p in command.permissions):
                raise ValueError("Permissions must be a list of strings")
            specs = [spec for plugin in await self._plugins.list_plugins() for spec in plugin.get("tool_specs", [])]
            spec = next((s for s in specs if s["name"] == command.tool_name), None)
            if spec is None or not set(command.permissions) <= set(spec["permissions"]):
                raise ValueError("Unknown tool or undeclared permissions")
            self._permissions.set_grants(command.tool_name, command.permissions)
        elif isinstance(command, ResolveToolPermissionCommand):
            self._permissions.resolve(command.request_id, command.allowed, command.remember)
        else:
            raise ValueError("Unknown permissions command")
        await self._bus.publish(PluginListReceived(plugins=await plugin_list(self._plugins, self._permissions)))
