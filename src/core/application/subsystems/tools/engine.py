from src.core.application.ports.event_port import EventBusPort
from src.core.domain.value_objects.tool import ToolCall, ToolResult, ToolSpec
from src.core.domain.value_objects.tool import ToolPermission
import asyncio
import inspect
import math
import json
from src.core.domain.value_objects.tool import ToolParameter
from src.core.application.ports.tools_port import ToolRegistryPort
from src.core.domain.entities.user import User
from src.core.domain.events.tool_events import ToolExecuted, ToolExecution
from src.core.utils.logger import logger
logger = logger.get(__name__)


class ToolEngine:
    """
    Логика tools-подсистемы.
    """

    def __init__(
        self,
        registry: ToolRegistryPort,
        event_bus: EventBusPort,
        jobs=None,
        permissions=None,
    ):
        self._registry = registry
        self._bus = event_bus
        self._jobs = jobs
        self._permissions = permissions
        self._job_specs = {}
        if jobs is not None:
            for name, description in (
                ("jobs_status", "Read a background job's status, progress and result"),
                ("jobs_cancel", "Cancel a background job started for this user"),
                ("jobs_list", "List this user's recent background jobs"),
            ):
                params = {} if name == "jobs_list" else {
                    "job_id": ToolParameter("job_id", "string", "Job ID returned when the tool started")}
                self._job_specs[name] = ToolSpec(name, description, params, (ToolPermission.READ,), "builtin")

    async def execute(self, call: ToolCall, user: User) -> ToolResult:
        logger.info(f"[ToolEngine] execute {call.name}({call.arguments})")

        # 1. Находим spec
        if not isinstance(call.name, str) or not call.name.strip():
            return ToolResult.fail("invalid", "Tool name must be a nonempty string")
        spec = self._job_specs.get(call.name) or await self._registry.get_spec(call.name)
        if spec is None:
            return ToolResult.fail(call.name, f"Unknown tool: {call.name}")
        if not isinstance(call.arguments, dict):
            return ToolResult.fail(call.name, "Arguments must be an object")
        if self._permissions is None and any(permission != ToolPermission.READ for permission in spec.permissions):
            return ToolResult.fail(call.name, "Only read-only tools are enabled in this version")
        for name, parameter in spec.parameters.items():
            if parameter.required and name not in call.arguments:
                return ToolResult.fail(call.name, f"Missing argument: {name}")
            if name in call.arguments:
                value = call.arguments[name]
                types = {"string": str, "integer": int, "number": (int, float),
                         "boolean": bool, "array": list, "object": dict}
                expected = types.get(parameter.type)
                valid = expected is not None and isinstance(value, expected)
                if parameter.type in ("integer", "number"):
                    valid = valid and not isinstance(value, bool) and (not isinstance(value, float) or math.isfinite(value))
                if not valid:
                    return ToolResult.fail(call.name, f"{name} must be {parameter.type}")
                if parameter.enum is not None and value not in parameter.enum:
                    return ToolResult.fail(call.name, f"{name} is not an allowed value")
        if set(call.arguments) - set(spec.parameters):
            return ToolResult.fail(call.name, "Unknown arguments")

        if call.name in self._job_specs:
            try:
                if call.name == "jobs_list":
                    output = self._jobs.list(user.id)
                elif call.name == "jobs_cancel":
                    output = await self._jobs.cancel(user.id, call.arguments["job_id"])
                else:
                    output = self._jobs.status(user.id, call.arguments["job_id"])
                return ToolResult.ok(call.name, json.dumps(output, ensure_ascii=False))
            except ValueError as exc:
                return ToolResult.fail(call.name, str(exc))

        # 3. Получаем handler
        handler = await self._registry.get_handler(call.name)
        if handler is None:
            return ToolResult.fail(call.name, "Tool handler not found")

        if self._permissions is not None:
            try:
                if not await self._permissions.authorize(spec, user.id):
                    return ToolResult.fail(call.name, "Пользователь не разрешил доступ. Не повторяй этот вызов без его просьбы.")
            except Exception as exc:
                logger.exception("Tool permission check failed")
                return ToolResult.fail(call.name, f"Permission check failed: {exc}")

        # 4. Выполняем
        await self._bus.publish(ToolExecution(
            tool_name=call.name,
            parameters=call.arguments,
        ))

        try:
            async def invoke():
                if inspect.iscoroutinefunction(handler) or inspect.iscoroutinefunction(getattr(handler, "__call__", None)):
                    return await handler(**call.arguments)
                result = await asyncio.to_thread(handler, **call.arguments)
                return await result if inspect.isawaitable(result) else result
            if spec.background:
                if self._jobs is None:
                    raise RuntimeError("Background jobs are unavailable")
                async def operation(progress):
                    if hasattr(handler, "run"):
                        return await handler.run(call.arguments, progress)
                    return await invoke()
                output = json.dumps(self._jobs.submit(user.id, call.name, operation, spec.timeout_seconds))
            else:
                output = await asyncio.wait_for(invoke(), timeout=spec.timeout_seconds)
            output_str = str(output)[:4000]
            await self._bus.publish(ToolExecuted(
                tool_name=call.name,
                result=output_str,
                parameters=call.arguments,
                success=True,
            ))
            logger.info(f"[ToolEngine] success: {output_str!r}")
            return ToolResult.ok(call.name, output_str)
        except Exception as e:
            logger.error(f"[ToolEngine] {call.name} failed")
            await self._bus.publish(ToolExecuted(
                tool_name=call.name,
                result=None,
                parameters=call.arguments,
                success=False,
                error_message=str(e),
            ))
            return ToolResult.fail(call.name, str(e))
        
    async def get_available_tools(self) -> list[ToolSpec]:
        return [spec for spec in await self._registry.get_available()
                if self._permissions is not None or all(p == ToolPermission.READ for p in spec.permissions)] + list(self._job_specs.values())
