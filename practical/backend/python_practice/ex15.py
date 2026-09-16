"""
Rate Limiter

Implement is_allowed(user_id, timestamp).

You are building a simple per-user API rate limiter.

Rules:

* A user can make at most 3 requests in any rolling 10-second window.
* timestamp is an integer number of seconds.
* Calls arrive in non-decreasing timestamp order.
* Return True if the request is allowed.
* Return False if the request should be rejected.

Example:

limiter = RateLimiter()
limiter.is_allowed("u1", 1)   -> True
limiter.is_allowed("u1", 2)   -> True
limiter.is_allowed("u1", 3)   -> True
limiter.is_allowed("u1", 4)   -> False
limiter.is_allowed("u1", 11)  -> True

Senior follow-up:

How would this need to change for multiple web servers behind a load balancer?
"""

from collections import defaultdict, deque

class RateLimiter:

    def __init__(self):
        # user_id -> deque of timestamps
        self.requests = defaultdict(deque)

    def is_allowed(self, user_id: str, timestamp: int) -> bool:

        user_requests = self.requests[user_id]
        # Remove requests outside the rolling 10-second window
        while user_requests and user_requests[0] <= timestamp - 10:
            user_requests.popleft()
        # Reject if user already made 3 requests
        if len(user_requests) >= 3:
            return False
        # Accept request and store timestamp
        user_requests.append(timestamp)

        return True


if __name__ == "__main__":
    limiter = RateLimiter()
    assert limiter.is_allowed("u1", 1) is True
    assert limiter.is_allowed("u1", 2) is True
    assert limiter.is_allowed("u1", 3) is True
    assert limiter.is_allowed("u1", 4) is False
    assert limiter.is_allowed("u2", 4) is True
    assert limiter.is_allowed("u1", 11) is True
    assert limiter.is_allowed("u1", 12) is True
    assert limiter.is_allowed("u1", 13) is True
    assert limiter.is_allowed("u1", 14) is False

    print("All tests passed!")
