"""HttpOnly browser sessions with strict origin checks on cookie-authenticated writes."""
from fastapi import HTTPException, Request, Response

from app.core.config import settings

ACCESS_COOKIE = "am_browser_access"
REFRESH_COOKIE = "am_browser_refresh"
ACCESS_PATH = "/api/v1"
REFRESH_PATH = "/api/v1/auth/browser"


def require_browser_origin(request: Request) -> None:
    # Only the configured web frontend may initiate browser authentication/writes.
    # Native clients keep using explicit bearer credentials, never these cookies.
    if request.headers.get("origin") != settings.FRONTEND_URL.rstrip("/"):
        raise HTTPException(403, "Originea cererii nu este autorizată.")


def set_browser_cookies(response: Response, access: str, refresh: str) -> None:
    options = {"httponly": True, "secure": settings.is_production, "samesite": "lax"}
    response.set_cookie(ACCESS_COOKIE, access, path=ACCESS_PATH,
                        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, **options)
    response.set_cookie(REFRESH_COOKIE, refresh, path=REFRESH_PATH,
                        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, **options)
    response.headers["Cache-Control"] = "no-store"


def clear_browser_cookies(response: Response) -> None:
    for name, path in [(ACCESS_COOKIE, ACCESS_PATH), (REFRESH_COOKIE, REFRESH_PATH)]:
        response.delete_cookie(name, path=path, httponly=True,
                               secure=settings.is_production, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
