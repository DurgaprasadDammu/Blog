# pyrefly: ignore [missing-import]
from slowapi import Limiter
# pyrefly: ignore [missing-import]
from slowapi.util import get_remote_address

# Shared limiter instance. Keyed by client IP by default.
# Used specifically to rate-limit comment creation to prevent spam.
limiter = Limiter(key_func=get_remote_address)
