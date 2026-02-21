import time
from collections import deque
from fastapi import HTTPException, Request

class SlidingWindowRateLimiter:
    """
    In-memory sliding window rate limiter.
    O(1) checks, O(K) space where K is max requests in window.
    """
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.clients = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.clients:
            self.clients[client_id] = deque()
        
        window = self.clients[client_id]
        
        # Evict old timestamps
        while window and window[0] <= now - 60:
            window.popleft()
            
        if len(window) < self.requests_per_minute:
            window.append(now)
            return True
        return False

# Professional default: 100 requests/minute per IP
rate_limiter = SlidingWindowRateLimiter(requests_per_minute=100)

async def rate_limit_dependency(request: Request):
    """FastAPI dependency for endpoint-level rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        from app.core.logging import logger
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please try again in a minute."
        )
