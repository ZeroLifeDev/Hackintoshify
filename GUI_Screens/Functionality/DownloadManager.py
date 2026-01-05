# GUI_Screens/Functionality/DownloadManager.py

import os
import json
import time
import requests
from PySide6.QtCore import QObject, Signal, QThread,  QMutex, QMutexLocker

DOWNLOAD_STATE_FILE = "download_state.json"
CHUNK_SIZE = 8192

class DownloadWorker(QObject):
    # Signals
    progress = Signal(int, str, int, int) # progress_pct, speed_str, bytes_downloaded, total_bytes
    finished = Signal()
    error = Signal(str)
    status_changed = Signal(str) # "Downloading", "Paused", "Finished", "Error"

    def __init__(self, url, dest_path, parent=None):
        super().__init__(parent)
        self.url = url
        self.dest_path = dest_path
        self.part_path = dest_path + ".part"
        
        self.is_paused = False
        self.is_cancelled = False
        self.is_running = False
        
        self.total_size = 0
        self.downloaded_size = 0
        self.start_time = 0
        self.speed = "0 KB/s"
        
        # Init state
        if os.path.exists(self.part_path):
            self.downloaded_size = os.path.getsize(self.part_path)
            
    def start_download(self):
        self.is_running = True
        self.is_paused = False
        self.is_cancelled = False
        self.status_changed.emit("Downloading")
        
        try:
            # Check total size if possible (HEAD request)
            if self.total_size == 0:
                head = requests.head(self.url, allow_redirects=True)
                if 'content-length' in head.headers:
                    self.total_size = int(head.headers.get('content-length'))
            
            # Force HTTPS
            if self.url.startswith('http://'):
                self.url = self.url.replace('http://', 'https://', 1)

            headers = {
                'User-Agent': 'InternetRecovery/1.0'
            }
            mode = 'wb'
            if self.downloaded_size > 0:
                headers['Range'] = f"bytes={self.downloaded_size}-"
                mode = 'ab' # Append
                
            response = requests.get(self.url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # If server doesn't support range, it sends 200 instead of 206
            # We must detect this to verify resume support
            is_resumed = (response.status_code == 206)
            if self.downloaded_size > 0 and not is_resumed:
                # Server ignored range, must restart
                self.downloaded_size = 0
                mode = 'wb'
            
            # If total size was missing from HEAD, get from GET
            if self.total_size == 0 and 'content-length' in response.headers:
                self.total_size = int(response.headers['content-length']) + self.downloaded_size
            
            self.start_time = time.time()
            bytes_in_session = 0
            
            with open(self.part_path, mode) as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if self.is_cancelled:
                        f.close()
                        self.cleanup()
                        return
                        
                    if self.is_paused:
                        self.status_changed.emit("Paused")
                        return # Exit run loop, state is saved on disk
                        
                    if chunk:
                        f.write(chunk)
                        chunk_len = len(chunk)
                        self.downloaded_size += chunk_len
                        bytes_in_session += chunk_len
                        
                        # Calculate Speed
                        elapsed = time.time() - self.start_time
                        if elapsed > 1.0:
                             speed_val = bytes_in_session / elapsed
                             self.speed = self.format_speed(speed_val)
                             
                        # Emit Progress
                        pct = 0
                        if self.total_size > 0:
                            pct = int((self.downloaded_size / self.total_size) * 100)
                        
                        self.progress.emit(pct, self.speed, self.downloaded_size, self.total_size)

            # Success
            os.rename(self.part_path, self.dest_path)
            self.status_changed.emit("Finished")
            self.finished.emit()
            self.is_running = False

        except Exception as e:
            self.status_changed.emit("Error")
            self.error.emit(str(e))
            self.is_running = False

    def pause(self):
        self.is_paused = True
    
    def cancel(self):
        self.is_cancelled = True
        
    def cleanup(self):
        if os.path.exists(self.part_path):
            os.remove(self.part_path)
        if os.path.exists(self.dest_path):
            os.remove(self.dest_path)

    def format_speed(self, bytes_per_sec):
        if bytes_per_sec > 1024 * 1024:
            return f"{bytes_per_sec / (1024*1024):.1f} MB/s"
        elif bytes_per_sec > 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec:.0f} B/s"

class DownloadManager(QObject):
    # Singleton-like management of downloads
    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloads = [] # List of dicts { 'uuid':.., 'worker':.., 'thread':.. }
        self.load_state()

    def start_download(self, url, dest_path, uuid=None):
        # Create Worker
        worker = DownloadWorker(url, dest_path)
        thread = QThread()
        worker.moveToThread(thread)
        
        # Connect
        thread.started.connect(worker.start_download)
        worker.finished.connect(thread.quit)
        # worker.finished.connect(worker.deleteLater) # Keep worker alive to see status?
        thread.finished.connect(thread.deleteLater)
        
        # Store
        task = {
            'url': url,
            'path': dest_path,
            'worker': worker,
            'thread': thread,
            'status': 'Pending'
        }
        self.downloads.append(task)
        
        thread.start()
        self.save_state()
        return worker

    def load_state(self):
        # TODO: Implement full state restoration from JSON
        # For now, we mainly rely on file existence
        pass

    def save_state(self):
        # TODO: Save active downloads to JSON
        pass
