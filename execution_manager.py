import threading
import subprocess
import queue
import os
import signal
import sys

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
            return False

        self.full_logs = f"### Starting Execution...\n$ {command}\n"
        self.is_running = True
        
        def run_proc():
            try:
                # On Unix, setsid creates a new process group so we can kill the whole group
                preexec = os.setsid if os.name == 'posix' else None
                
                self.process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env,
                    preexec_fn=preexec
                )
                
                for line in self.process.stdout:
                    self.output_queue.put(line)
                    self.full_logs += line
                
                self.process.wait()
            except Exception as e:
                self.full_logs += f"\n[ERROR] Process Exception: {e}\n"
            finally:
                self.is_running = False
                self.process = None

        self.thread = threading.Thread(target=run_proc, daemon=True)
        self.thread.start()
        return True

    def stop_execution(self):
        """Terminates the running process tree."""
        if self.process and self.is_running:
            try:
                self.full_logs += "\n[INFO] Stopping execution...\n"
                
                if os.name == 'nt': # Windows
                    # /F = Force, /T = Tree (kill children like behave.exe)
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
                else: # Linux/Mac
                    # Kill the process group
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                self.is_running = False
                return True
            except Exception as e:
                self.full_logs += f"\n[ERROR] Failed to stop: {e}\n"
                return False
        return False

    def get_new_logs(self):
        new_lines = ""
        while not self.output_queue.empty():
            try:
                new_lines += self.output_queue.get_nowait()
            except queue.Empty:
                break
        return new_lines
