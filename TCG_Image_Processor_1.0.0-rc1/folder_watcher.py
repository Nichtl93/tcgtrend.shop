
import threading
from watchdog.events import FileSystemEventHandler

class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, callback, delay=2.0):
        super().__init__()
        self.callback = callback
        self.delay = delay
        self.timer = None
        self.lock = threading.Lock()

    def schedule(self):
        with self.lock:
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(self.delay, self.callback)
            self.timer.daemon = True
            self.timer.start()

    def on_created(self, event):
        if not event.is_directory:
            self.schedule()

    def on_modified(self, event):
        if not event.is_directory:
            self.schedule()

    def on_moved(self, event):
        if not event.is_directory:
            self.schedule()
