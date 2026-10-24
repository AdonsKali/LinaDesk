import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timezone
from uuid import uuid4

from src.core.domain.events.tool_events import BackgroundJobFinished


ACTIVE = {"queued", "running"}


class BackgroundJobs:
    def __init__(self, event_bus, concurrency=2, capacity=8, history=100):
        if concurrency < 1 or capacity < concurrency or history < 1:
            raise ValueError("Invalid background job limits")
        self._bus = event_bus
        self._slots = asyncio.Semaphore(concurrency)
        self._capacity, self._history = capacity, history
        self._jobs = OrderedDict()
        self._tasks = {}
        self._closing = False

    def submit(self, owner, tool_name, operation, timeout):
        if self._closing:
            raise RuntimeError("Background jobs are stopping")
        if len(self._tasks) >= self._capacity:
            raise RuntimeError(f"Background job queue is full ({self._capacity} active jobs maximum)")
        job_id = uuid4().hex
        record = dict(job_id=job_id, tool_name=tool_name, status="queued", progress=None,
                      message="", result=None, error=None,
                      created_at=datetime.now(timezone.utc).isoformat())
        self._jobs[job_id] = (str(owner), record)
        task = asyncio.create_task(self._run(job_id, operation, timeout), name=f"plugin:{job_id}")
        self._tasks[job_id] = task
        task.add_done_callback(lambda done: self._tasks.pop(job_id, None))
        return dict(record)

    async def _run(self, job_id, operation, timeout):
        owner, record = self._jobs[job_id]
        def progress(value, message):
            if record["status"] == "running":
                record.update(progress=value, message=str(message)[:300])
        try:
            async with self._slots:
                record["status"] = "running"
                result = await asyncio.wait_for(operation(progress), timeout)
                record.update(status="succeeded", result=str(result)[:4000], progress=100)
        except asyncio.CancelledError:
            record["status"] = "cancelled"
        except asyncio.TimeoutError:
            record.update(status="timed_out", error="Background job exceeded its time limit")
        except Exception as exc:
            record.update(status="failed", error=str(exc)[:1000])
        finally:
            record["finished_at"] = datetime.now(timezone.utc).isoformat()
            try:
                await self._bus.publish(BackgroundJobFinished(
                    job_id=job_id, tool_name=record["tool_name"], user_id=owner,
                    status=record["status"], result=record["result"], error=record["error"]))
            except Exception:
                logging.getLogger(__name__).exception("Could not publish background job notification")
            finally:
                terminal = [key for key, (_, item) in self._jobs.items() if item["status"] not in ACTIVE]
                for key in terminal[:-self._history]:
                    self._jobs.pop(key, None)

    def status(self, owner, job_id):
        stored = self._jobs.get(job_id)
        if stored is None or stored[0] != str(owner):
            raise ValueError("Background job not found")
        return dict(stored[1])

    def list(self, owner):
        return [{key: item[key] for key in ("job_id", "tool_name", "status", "progress")}
                for user, item in self._jobs.values() if user == str(owner)]

    async def cancel(self, owner, job_id):
        self.status(owner, job_id)
        task = self._tasks.get(job_id)
        if task is not None and not task.done():
            # Let a newly submitted coroutine enter its cancellation handler first.
            await asyncio.sleep(0)
            if not task.done():
                if not task.cancelling():
                    task.cancel()
                await asyncio.shield(task)
        return self.status(owner, job_id)

    async def close(self):
        self._closing = True
        await asyncio.sleep(0)
        tasks = list(self._tasks.values())
        for task in tasks:
            if not task.done() and not task.cancelling():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
