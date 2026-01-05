# GUI_Screens/Functionality/DownloadManager.py

import os
import json
import time
import requests
from PySide6.QtCore import QObject, Signal, QThread,  QMutex, QMutexLocker

import sys

def get_state_file_path():
    if sys.platform == "win32":
        config_dir = os.path.join(os.getenv("ProgramData"), "Hackintoshify")
    elif sys.platform == "darwin":
        config_dir = "/Library/Application Support/Hackintoshify"
    else:
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "hackintoshify")
    
    if not os.path.exists(config_dir):
        try: os.makedirs(config_dir, exist_ok=True)
        except: pass
        
    return os.path.join(config_dir, "download_state.json")

DOWNLOAD_STATE_FILE = get_state_file_path()
CHUNK_SIZE = 8192

class DownloadWorker(QObject):
    # Signals
    # Use float for sizes to avoid 32-bit int overflow on large files (>2GB)
    progress = Signal(int, str, float, float) # pct, speed, dl_size, total_size
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
            # Suppress SSL warnings globally for this worker
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Check total size if possible (HEAD request) - MUST use verify=False
            if self.total_size == 0:
                try:
                    head = requests.head(self.url, allow_redirects=True, verify=False, timeout=10)
                    if 'content-length' in head.headers:
                        self.total_size = int(head.headers.get('content-length'))
                except:
                    pass # HEAD failed, ignore and rely on GET
            
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
                
            response = requests.get(self.url, headers=headers, stream=True, timeout=30, verify=False)
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
                             
                        try:
                            if self.total_size > 0:
                                pct = int((float(self.downloaded_size) / float(self.total_size)) * 100)
                                if pct < 0: pct = 0
                                if pct > 100: pct = 100
                            else:
                                pct = 0
                                
                            self.progress.emit(int(pct), self.speed, int(self.downloaded_size), int(self.total_size))
                        except Exception:
                            pass # Avoid overflow errors disrupting logic

            # Success
            if os.path.exists(self.dest_path):
                os.remove(self.dest_path) # Prevent WinError 183
            os.rename(self.part_path, self.dest_path)
            self.status_changed.emit("Finished")
            self.finished.emit()
            self.is_running = False

        except Exception as e:
            print(f"Download Worker Error: {e}")
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

    def set_status(self, status):
        self.status_changed.emit(status)

class DownloadManager(QObject):
    task_added = Signal(dict) # Emit when a task is loaded from disk

    def __init__(self, parent=None):
        super().__init__(parent)
        self.downloads = [] 
        self.load_state()
        # Structure: { 'url':str, 'path':str, 'name':str, 'worker':Obj, 'thread':Obj, 'status':str }

    def start_download(self, url, dest_path, name="Unknown"):
        # Check if already exists in list (resume case handled separately)
        for task in self.downloads:
            if task['path'] == dest_path and task['status'] not in ['Cancelled', 'Finished']:
                if task['status'] == 'Paused':
                    self.resume_download(task)
                    return task['worker']
                return task['worker'] 

        worker, thread = self._create_worker_thread(url, dest_path)
        
        task = {
            'url': url,
            'path': dest_path,
            'name': name,
            'worker': worker,
            'thread': thread,
            'status': 'Pending'
        }
        self.downloads.append(task)
        
        thread.start()
        self.save_state()
        return worker

    def _create_worker_thread(self, url, dest_path):
        worker = DownloadWorker(url, dest_path)
        # Parent the thread to self (DownloadManager) so it isn't GC'd unexpectedly while running
        thread = QThread(self) 
        worker.moveToThread(thread)
        
        thread.started.connect(worker.start_download)
        worker.finished.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        # worker is implicitly destroyed when Python GC collects it if check parentage, 
        # but better to handle cleanup explicitly if needed. Python GC is usually fine here.
        
        return worker, thread

    def resume_download(self, task):
        # Create new worker/thread for the existing task
        if task['status'] == 'Downloading': return
        
        # Clean up old refs if any
        if task.get('thread'):
            if task['thread'].isRunning(): task['thread'].quit()
            task['thread'] = None
        
        url = task['url']
        path = task['path']
        
        worker, thread = self._create_worker_thread(url, path)
        task['worker'] = worker
        task['thread'] = thread
        task['status'] = 'Pending'
        
        thread.start()
        self.save_state()
        return worker

    def pause_download(self, task):
        if task['worker']:
            task['worker'].pause()
            task['status'] = 'Paused'
        self.save_state()

    def cancel_download(self, task):
        if task['worker']:
            task['worker'].cancel()
        
        # Mark cancelled logic handled in worker cleanup, but we update list
        task['status'] = 'Cancelled'
        if task in self.downloads:
            self.downloads.remove(task)
        self.save_state()
        
    def pause_all(self):
        for task in self.downloads:
            if task['status'] == 'Downloading' and task['worker']:
                task['worker'].pause()
                task['status'] = 'Paused'
        self.save_state()

    def load_state(self):
        if not os.path.exists(DOWNLOAD_STATE_FILE): return
        
        try:
            with open(DOWNLOAD_STATE_FILE, 'r') as f:
                data = json.load(f)
                
            for item in data:
                # We don't auto-start, just load into list as Paused
                # Check if file part exists -> "Paused", else "Error" or "Finished" logic
                path = item['path']
                status = "Paused"
                
                # Verify partial or full file presence
                if os.path.exists(path):
                    status = "Finished" 
                    # We WANT to show finished tasks so user can delete them
                elif os.path.exists(path + ".part"):
                    status = "Paused"
                else:
                    # File gone, maybe start fresh?
                    # If we don't save "Pending", we lose retries. Default to Paused (Resumable from 0)
                    status = "Paused" 

                task = {
                    'url': item['url'],
                    'path': path,
                    'name': item.get('name', 'Unknown'),
                    'worker': None,
                    'thread': None,
                    'status': status
                }
                self.downloads.append(task)
                self.task_added.emit(task) 
                
        except Exception as e:
            print(f"Error loading state: {e}")

    def save_state(self):
        data = []
        for task in self.downloads:
            # Don't save Cancelled (removed), but DO save Finished so user can see/delete them later
            if task['status'] == 'Cancelled': continue
            
            data.append({
                'url': task['url'],
                'path': task['path'],
                'name': task.get('name', 'Unknown'),
                'status': task['status']
            })
            
        try:
            with open(DOWNLOAD_STATE_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving state: {e}")
