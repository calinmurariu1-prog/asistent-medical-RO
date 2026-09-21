import pyotp
from sqlalchemy import select

from app.models.user import AuditLog
from tests.test_gdpr import API, _auth


def test_identifier_export_is_opt_in_reauthenticated_and_owner_scoped(client, db_session):
    owner = _auth(client, "identifier-owner@example.com")
    other = _auth(client, "identifier-other@example.com")
    client.put(f"{API}/patients/me", headers=owner, json={"cnp": "0000000000000"})
    client.put(f"{API}/patients/me", headers=other, json={"cnp": "1111111111111"})
    assert "0000000000000" not in client.get(f"{API}/gdpr/export", headers=owner).text
    for payload in [{"password": "Parola1234"}, {"password": "wrong", "include_cnp": True}]:
        assert client.post(f"{API}/gdpr/export/with-identifier", headers=owner,
                           json=payload).status_code == 400
    response = client.post(f"{API}/gdpr/export/with-identifier", headers=owner,
                           json={"password": "Parola1234", "include_cnp": True})
    assert response.status_code == 200
    assert response.json()["patient"]["cnp"] == "0000000000000"
    assert "1111111111111" not in response.text
    assert "cnp" not in response.json()["export_metadata"]["not_included"]
    assert response.headers["cache-control"] == "no-store"
    logs = list(db_session.scalars(select(AuditLog).where(
        AuditLog.action == "gdpr_export_with_identifier")))
    assert len(logs) == 1 and logs[0].detail is None


def test_identifier_export_enforces_mfa_and_consumes_backup_once(client):
    headers = _auth(client, "identifier-mfa@example.com")
    client.put(f"{API}/patients/me", headers=headers, json={"cnp": "0000000000000"})
    secret = client.post(f"{API}/auth/mfa/setup", headers=headers).json()["secret"]
    codes = client.post(f"{API}/auth/mfa/activate", headers=headers,
                        json={"code": pyotp.TOTP(secret).now()}).json()["recovery_codes"]
    token = client.post(f"{API}/auth/login", json={"email": "identifier-mfa@example.com",
        "password": "Parola1234", "mfa_code": pyotp.TOTP(secret).now()}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"password": "Parola1234", "include_cnp": True}
    assert client.post(f"{API}/gdpr/export/with-identifier", headers=headers,
                       json=payload).status_code == 400
    payload["mfa_code"] = codes[0]
    assert client.post(f"{API}/gdpr/export/with-identifier", headers=headers,
                       json=payload).status_code == 200
    assert client.post(f"{API}/gdpr/export/with-identifier", headers=headers,
                       json=payload).status_code == 400
