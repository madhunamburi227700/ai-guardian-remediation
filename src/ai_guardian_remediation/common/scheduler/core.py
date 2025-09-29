import time
import logging
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from ai_guardian_remediation.common.scheduler.task_cleanup import cleanup_dirs


class Task:
    def __init__(self, name, func, interval_seconds):
        self.name = name
        self.func = func
        self.interval = interval_seconds
        self.next_run = datetime.now() + timedelta(seconds=self.interval)
        self._executor = ThreadPoolExecutor(max_workers=1)

    def should_run(self):
        return datetime.now() >= self.next_run

    def run(self):
        logging.info(f"Running task: {self.name} at {datetime.now()}")
        try:
            future = self._executor.submit(self.func)
            future.result()
        except Exception as e:
            logging.error(f"Error running task {self.name}: {e}")
        self.next_run = datetime.now() + timedelta(seconds=self.interval)


class Scheduler:
    def __init__(self):
        self.tasks = []
        self.running = False
        self._thread = None

    def add_task(self, task):
        self.tasks.append(task)

    def _run(self):
        while self.running:
            for task in self.tasks:
                if task.should_run():
                    task.run()
            time.sleep(1)

    def start(self):
        if self._thread is not None:
            return

        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logging.info("Scheduler started.")
        return self

    def stop(self):
        if self._thread is None:
            return

        self.running = False
        self._thread.join()
        self._thread = None
        logging.info("Scheduler stopped.")


def schedule_tasks():
    scheduler = Scheduler()
    scheduler.add_task(Task("Cleanup Repos", cleanup_dirs, 3600))
    return scheduler.start()
