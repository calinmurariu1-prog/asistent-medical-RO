from app.core.browser_session import ACCESS_COOKIE, REFRESH_COOKIE
from app.core.config import settings

API = "/api/v1"
CREDENTIALS = {"email": "cookie@example.com", "password": "Cookie-password123"}


def register(client):
    assert client.post(API + "/auth/register", json=CREDENTIALS).status_code == 201


def login(client):
    return client.post(API + "/auth/browser/login", json=CREDENTIALS,
                       headers={"Origin": settings.FRONTEND_URL})


def test_cookie_login_hides_tokens_and_refreshes(client):
    register(client)
    result = login(client)
    assert result.status_code == 200
    assert "token" not in result.text
    assert client.cookies.get(ACCESS_COOKIE)
    assert client.cookies.get(REFRESH_COOKIE)
    assert all("HttpOnly" in c and "SameSite=lax" in c
               for c in result.headers.get_list("set-cookie"))
    assert client.get(API + "/auth/me").status_code == 200
    client.cookies.delete(ACCESS_COOKIE)
    assert client.get(API + "/auth/me").status_code == 401
    refreshed = client.post(API + "/auth/browser/refresh",
                            headers={"Origin": settings.FRONTEND_URL})
    assert refreshed.status_code == 200
    assert "token" not in refreshed.text
    assert client.get(API + "/auth/me").status_code == 200


def test_cross_site_login_and_cookie_writes_rejected(client):
    register(client)
    for headers in [{}, {"Origin": "https://evil.example"}, {"Origin": "null"}]:
        assert client.post(API + "/auth/browser/login", json=CREDENTIALS,
                           headers=headers).status_code == 403
    assert login(client).status_code == 200
    for headers in [{}, {"Origin": "https://evil.example"}]:
        assert client.post(API + "/auth/logout-all", headers=headers).status_code == 403
        assert client.post(API + "/auth/browser/refresh", headers=headers).status_code == 403
    assert client.get(API + "/auth/me").status_code == 200


def test_cookie_logout_revokes_bearer_and_clears_cookies(client):
    register(client)
    bearer = client.post(API + "/auth/login", json=CREDENTIALS).json()["access_token"]
    assert login(client).status_code == 200
    result = client.post(API + "/auth/browser/logout-all",
                         headers={"Origin": settings.FRONTEND_URL})
    assert result.status_code == 200
    assert not client.cookies.get(ACCESS_COOKIE)
    assert not client.cookies.get(REFRESH_COOKIE)
    assert client.get(API + "/auth/me",
                      headers={"Authorization": "Bearer " + bearer}).status_code == 401


def test_cookie_login_production_secure(client, monkeypatch):
    register(client)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    result = login(client)
    assert all("Secure" in c for c in result.headers.get_list("set-cookie"))
    assert result.headers["cache-control"] == "no-store"


def test_bearer_native_writes_remain_supported(client):
    register(client)
    tokens = client.post(API + "/auth/login", json=CREDENTIALS).json()
    result = client.post(API + "/auth/logout-all",
                         headers={"Authorization": "Bearer " + tokens["access_token"]})
    assert result.status_code == 200
