import time
from threading import Lock
from typing import Optional

_token_blacklist: dict[str, float] = {}
_blacklist_lock = Lock()

BLACKLIST_CHECK_ENABLED = True

def add_token_to_blacklist(jti: str, exp: float) -> None:
    with _blacklist_lock:
        _token_blacklist[jti] = exp

def is_token_blacklisted(jti: str) -> bool:
    if not BLACKLIST_CHECK_ENABLED:
        return False
    with _blacklist_lock:
        _cleanup_expired()
        return jti in _token_blacklist

def _cleanup_expired() -> None:
    now = time.time()
    expired = [jti for jti, exp in _token_blacklist.items() if exp < now]
    for jti in expired:
        del _token_blacklist[jti]

def get_blacklist_size() -> int:
    with _blacklist_lock:
        _cleanup_expired()
        return len(_token_blacklist)
