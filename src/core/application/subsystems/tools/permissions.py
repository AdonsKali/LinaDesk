import asyncio
from uuid import uuid4

from src.core.domain.events.tool_events import ToolPermissionRequested, ToolPermissionRequestClosed
from src.core.domain.value_objects.tool import ToolPermission


class ToolPermissions:
    def __init__(self, store, event_bus, request_timeout=120):
        self._store, self._bus = store, event_bus
        self._timeout = request_timeout
        self._pending = {}

    def granted(self, tool_name):
        return self._store.get(tool_name)

    def set_grants(self, tool_name, permissions):
        values = sorted({ToolPermission(value).value for value in permissions})
        self._store.set(tool_name, values)
        for future, spec, _ in tuple(self._pending.values()):
            if spec.name == tool_name and not future.done() and {p.value for p in spec.permissions} <= set(values):
                future.set_result(True)

    async def authorize(self, spec, user_id):
        if spec.trusted_builtin:
            return True
        required = {p.value for p in spec.permissions}
        missing = sorted(required - set(self.granted(spec.name)))
        if not missing:
            return True
        if len(self._pending) >= 4:
            return False
        request_id = uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self._pending[request_id] = (future, spec, missing)
        try:
            await self._bus.publish(ToolPermissionRequested(
                request_id=request_id, tool_name=spec.name, plugin_name=spec.plugin_name,
                user_id=str(user_id), permissions=missing))
            allowed = await asyncio.wait_for(future, self._timeout)
            return allowed and required <= (set(self.granted(spec.name)) | set(missing))
        except asyncio.TimeoutError:
            return False
        finally:
            self._pending.pop(request_id, None)
            await self._bus.publish(ToolPermissionRequestClosed(request_id=request_id))

    def resolve(self, request_id, allowed, remember=False):
        if type(allowed) is not bool or type(remember) is not bool:
            raise ValueError("Permission decision must be boolean")
        pending = self._pending.get(request_id)
        if pending is None or pending[0].done():
            return False
        future, spec, missing = pending
        if allowed and remember:
            self.set_grants(spec.name, set(self.granted(spec.name)) | set(missing))
        if not future.done():
            future.set_result(allowed)
        return True

    def cancel_pending(self):
        for future, _, _ in tuple(self._pending.values()):
            if not future.done():
                future.set_result(False)
