import threading
import subprocess
import queue
import os

class ExecutionManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExecutionManager, cls).__new__(cls)
            cls._instance.process = None
            cls._instance.output_queue = queue.Queue()
            cls._instance.is_running = False
            cls._instance.full_logs = ""
            cls._instance.thread = None
        return cls._instance

    def start_execution(self, command, cwd, env):
        if self.is_running:
            return False # Already running

        self.full_logs = f"### Starting Execution...\n$ {command}\n"
        self.is_running = True
        
        def run_proc():
            try:
                self.process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env
                )
                
                for line in self.process.stdout:
                    self.output_queue.put(line)
                    self.full_logs += line
                
                self.process.wait()
            finally:
                self.is_running = False
                self.process = None

        self.thread = threading.Thread(target=run_proc, daemon=True)
        self.thread.start()
        return True

    def get_new_logs(self):
        """Retrieves new lines from the queue without blocking."""
        new_lines = ""
        while not self.output_queue.empty():
            try:
                new_lines += self.output_queue.get_nowait()
            except queue.Empty:
                break
        return new_lines
