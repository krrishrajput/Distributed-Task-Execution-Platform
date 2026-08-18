import asyncio
from app.queue.task_queue import TaskQueue
from app.core.logging import get_logger

logger = get_logger(__name__)

class LeaseManager:
    def __init__(self, task_queue: TaskQueue, renewal_interval: float):
        self.task_queue = task_queue
        self.renewal_interval = renewal_interval
        self._renewal_tasks = {}

    def start_renewal(self, task_id: str, worker_id: str, lease_id: str):
        if task_id in self._renewal_tasks:
            self._renewal_tasks[task_id].cancel()
        
        async def renewal_loop():
            try:
                while True:
                    await asyncio.sleep(self.renewal_interval)
                    success = await self.task_queue.renew_lease(task_id, worker_id, lease_id)
                    if not success:
                        logger.warning(f"Failed to renew lease for task {task_id}")
                        break
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in lease renewal for {task_id}: {e}")

        self._renewal_tasks[task_id] = asyncio.create_task(renewal_loop())

    def stop_renewal(self, task_id: str):
        task = self._renewal_tasks.pop(task_id, None)
        if task:
            task.cancel()
