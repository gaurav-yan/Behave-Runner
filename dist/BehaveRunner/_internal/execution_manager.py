import threading
import subprocess
import queue
import os
import signal
import sys
import re
import requests

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
            cls._instance.lt_session_ids = set()
        return cls._instance

    def start_execution(self, command, cwd, env):
        if self.is_running:
            return False

        self.full_logs = f"### Starting Execution...\n$ {command}\n"
        self.is_running = True
        self.lt_session_ids.clear()
        
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
                    
                    # Capture LambdaTest Session ID
                    # Common patterns: "SessionId: <guid>", "session_id=<guid>"
                    try:
                        # Pattern 1: SessionId: <guid>
                        match = re.search(r"SessionId:\s*([a-zA-Z0-9-]+)", line, re.IGNORECASE)
                        if match: self.lt_session_ids.add(match.group(1))
                        
                        # Pattern 2: session_id=<guid> (e.g. in URLs)
                        match = re.search(r"session_id=([a-zA-Z0-9-]+)", line, re.IGNORECASE)
                        if match: self.lt_session_ids.add(match.group(1))
                    except: pass
                
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
                
                # Check for cloud provider environment variables and attempt to stop session
                # This is a best-effort attempt to stop remote sessions if the local process is killed
                if os.environ.get('LT_USERNAME') and os.environ.get('LT_ACCESS_KEY'):
                    username = os.environ.get('LT_USERNAME')
                    access_key = os.environ.get('LT_ACCESS_KEY')
                    
                    if self.lt_session_ids:
                        self.full_logs += f"\n[INFO] Found LambdaTest Sessions to stop: {self.lt_session_ids}\n"
                        for session_id in self.lt_session_ids:
                            try:
                                url = f"https://api.lambdatest.com/automation/api/v1/sessions/{session_id}/stop"
                                response = requests.put(url, auth=(username, access_key))
                                if response.status_code == 200:
                                    self.full_logs += f"[INFO] Successfully stopped session {session_id}\n"
                                else:
                                    self.full_logs += f"[WARN] Failed to stop session {session_id}: {response.text}\n"
                            except Exception as e:
                                self.full_logs += f"[ERROR] Error stopping session {session_id}: {e}\n"
                    else:
                        self.full_logs += "\n[INFO] No LambdaTest Session IDs found in logs to stop.\n"

                elif os.environ.get('BROWSERSTACK_USERNAME') and os.environ.get('BROWSERSTACK_ACCESS_KEY'):
                    # Logic for BrowserStack session termination could go here
                    pass

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
