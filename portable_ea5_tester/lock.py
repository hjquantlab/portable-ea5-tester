"""
Process Lock and Mutual Exclusion for Strategy Tester.

Provides safe file-based mutual exclusion to prevent concurrent runs of the MT5
Strategy Tester in the same portable directory. Handles stale lock detection via
system PID verification. Standard library only.
"""

import os
import sys
import time
import ctypes
import contextlib
from typing import Optional


def is_process_running(pid: int) -> bool:
    """
    Checks if a process with the given PID is currently active.
    Uses Windows kernel32 OpenProcess via ctypes on Windows, or os.kill(pid, 0) on POSIX.
    """
    if pid <= 0:
        return False

    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    # Windows process verification via ctypes (standard library only)
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        exit_code = ctypes.c_ulong()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            STILL_ACTIVE = 259
            is_active = (exit_code.value == STILL_ACTIVE)
        else:
            is_active = True
        kernel32.CloseHandle(handle)
        return is_active
    return False


class TesterLock:
    """
    File-based mutual exclusion lock.
    Safely handles stale locks left behind by crashed or terminated processes.
    """

    __test__ = False

    def __init__(
        self,
        lock_path: str,
        timeout: float = 0.0,
        poll_interval: float = 0.5
    ) -> None:
        self.lock_path = os.path.abspath(lock_path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._acquired = False

    def acquire(self) -> bool:
        """
        Attempts to acquire the lock. If locked by another active process,
        waits up to self.timeout seconds. If timeout expires, raises TimeoutError.
        """
        start_time = time.time()
        my_pid = os.getpid()

        while True:
            if os.path.exists(self.lock_path):
                existing_pid: Optional[int] = None
                try:
                    with open(self.lock_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content.isdigit():
                        existing_pid = int(content)
                except Exception:
                    existing_pid = None

                if existing_pid == my_pid:
                    # Already owned by current process (re-entrant support)
                    self._acquired = True
                    return True

                if existing_pid and is_process_running(existing_pid):
                    elapsed = time.time() - start_time
                    if elapsed >= self.timeout:
                        raise TimeoutError(
                            f"[LOCK] Timed out after {self.timeout:.1f}s waiting for lock {self.lock_path} "
                            f"(held by active PID {existing_pid})."
                        )
                    time.sleep(self.poll_interval)
                    continue
                else:
                    # Stale lock: process does not exist
                    try:
                        os.remove(self.lock_path)
                    except OSError:
                        pass

            # Attempt to write lock file atomically or cleanly
            try:
                parent_dir = os.path.dirname(self.lock_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                with open(self.lock_path, "w", encoding="utf-8") as f:
                    f.write(str(my_pid))
                self._acquired = True
                return True
            except OSError as e:
                elapsed = time.time() - start_time
                if elapsed >= self.timeout:
                    raise TimeoutError(f"[LOCK] Failed to acquire lock {self.lock_path}: {e}")
                time.sleep(self.poll_interval)

    def release(self) -> None:
        """Releases the lock if owned by the current process."""
        if not self._acquired:
            return

        my_pid = str(os.getpid())
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content == my_pid:
                    os.remove(self.lock_path)
            except OSError:
                pass
        self._acquired = False

    def __enter__(self) -> "TesterLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


@contextlib.contextmanager
def acquire_tester_lock(lock_path: str, timeout: float = 0.0, poll_interval: float = 0.5):
    """Context manager helper for acquiring and releasing a TesterLock."""
    lock = TesterLock(lock_path, timeout=timeout, poll_interval=poll_interval)
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()
