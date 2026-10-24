import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    """Tiny in-memory limit per client IP. Protects your Gemini API key/quota from abuse.
    (One process only. Use Redis or an API gateway if you ever run several servers.)"""

    def __init__(self, limit: int = 20, window_seconds: int = 60):
        self.limit, self.window = limit, window_seconds
        self.hits = defaultdict(deque)

    def __call__(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        q = self.hits[ip]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
        q.append(now)
