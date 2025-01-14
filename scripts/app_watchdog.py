import os
import sys
import time
import signal
import logging
import subprocess
from datetime import datetime
from pathlib import Path

CHECK_INTERVAL = 60
TIMEOUT = 120
HEARTBEAT_FILE = "watchdog_heartbeat.txt"
class ApplicationWatchdog:
    def __init__(self, main_script: str):
        self.main_script = main_script
        self.process = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('watchdog.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create heartbeat file if it doesn't exist
        ApplicationWatchdog.Feed()
    @staticmethod
    def Feed():
        Path(HEARTBEAT_FILE).touch()
    def start_application(self):
        """Start the main application as a subprocess."""
        try:
            # Start the application with its own process group
            self.process = subprocess.Popen(
                [sys.executable, self.main_script],
                #preexec_fn=os.setsid  # Create new process group on Unix
            )
            self.logger.info(f"Started application (PID: {self.process.pid})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            return False
    
    def terminate_application(self):
        """Terminate the application and all its subprocesses."""
        if self.process:
            try:
                self.process.terminate()
                # Try graceful termination of the process group
                #os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait for termination
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    self.logger.warning("Force killing application...")
                    self.process.kill()
                    #os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                
                self.logger.info("Application terminated")
            except ProcessLookupError:
                self.logger.warning("Process already terminated")
            except Exception as e:
                self.logger.error(f"Error terminating application: {e}")
            
            self.process = None
    
    def check_heartbeat(self) -> bool:
        """Check if the heartbeat file has been updated recently."""
        try:
            mtime = os.path.getmtime(HEARTBEAT_FILE)
            time_since_update = time.time() - mtime
            return time_since_update <= TIMEOUT
        except Exception as e:
            self.logger.error(f"Error checking heartbeat: {e}")
            return False
    
    def monitor(self):
        """Main monitoring loop."""
        self.logger.info("Starting watchdog...")
        
        while True:
            try:
                # Start application if not running
                if not self.process or self.process.poll() is not None:
                    self.logger.warning("Application not running, starting...")
                    self.start_application()
                    time.sleep(CHECK_INTERVAL)  # Give application time to start
                    continue
                
                # Check heartbeat
                if not self.check_heartbeat():
                    self.logger.warning("Heartbeat missed, restarting application...")
                    self.terminate_application()
                    continue
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                self.logger.info("Watchdog stopped by user")
                self.terminate_application()
                break
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                self.terminate_application()
                time.sleep(1)

def main():
    # Create and start the watchdog
    watchdog = ApplicationWatchdog("scripts/main.py")
    
    # Handle termination signals
    def signal_handler(signum, frame):
        watchdog.logger.info("Received termination signal, shutting down...")
        watchdog.terminate_application()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start monitoring
    watchdog.monitor()

if __name__ == "__main__":
    main()