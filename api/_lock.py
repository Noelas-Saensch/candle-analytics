"""
Shared Groq rate-limit lock.
Both agents (agent.py, vibe_agent.py) acquire this before calling Groq API.
Serializes calls so free-tier rate limits are not exceeded.
"""

import os
import time
import logging

logger = logging.getLogger("groq_lock")

LOCK_FILE = "/tmp/groq_busy.lock"
MAX_WAIT = 30  # max seconds to wait for lock
POLL_INTERVAL = 0.5  # check every 500ms


def acquire_groq_lock(timeout=MAX_WAIT) -> bool:
    """Wait until the lock is free, then acquire it. Returns True if acquired."""
    waited = 0
    while waited < timeout:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            time.sleep(POLL_INTERVAL)
            waited += POLL_INTERVAL
    logger.warning("Could not acquire Groq lock after %ds — proceeding anyway", timeout)
    return False


def release_groq_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass
