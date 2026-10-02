"""One local process per data directory, including direct Uvicorn starts."""
import os
from pathlib import Path

_LOCKS = {}


class InstanceLock:
    def __init__(self, path):
        self.path = path
        self.file = path.open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if path.stat().st_size == 0:
                    self.file.write(b'0')
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('Data directory is in use or cannot be locked. Stop the other CyberAnt instance first.') from None

    def close(self):
        if self.file.closed:
            return
        if os.name == 'nt':
            import msvcrt
            self.file.seek(0)
            msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        self.file.close()
        _LOCKS.pop(self.path, None)
        # Never unlink: another process may already have opened this inode.


def acquire(data_dir):
    directory = Path(data_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / '.app-instance.lock'
    if path not in _LOCKS:
        _LOCKS[path] = InstanceLock(path)
    return _LOCKS[path]
