"""
HMAC callback signing — unit tests.

The system signs callbacks with HMAC-SHA256 and the
receiving system verifies with the same shared secret.
"""
import hashlib
import hmac
import json


HMAC_SECRET = "test-secret-key-for-hmac"


def sign_payload(payload: dict, secret: str = HMAC_SECRET) -> str:
    """Replicate the signing logic from stamp.py _sign_callback."""
    body = json.dumps(payload, ensure_ascii=False).encode()
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def verify_signature(payload: dict, signature: str, secret: str = HMAC_SECRET) -> bool:
    """Verify an incoming HMAC signature."""
    body = json.dumps(payload, ensure_ascii=False).encode()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


class TestHMACSigning:

    def test_sign_and_verify(self):
        payload = {"requestNo": "REQ-001", "status": "SUCCESS"}
        sig = sign_payload(payload)
        assert sig.startswith("sha256=")
        assert len(sig) == 71  # "sha256=" + 64 hex chars
        assert verify_signature(payload, sig)

    def test_tampered_payload_rejected(self):
        payload = {"requestNo": "REQ-001", "status": "SUCCESS"}
        sig = sign_payload(payload)
        payload["status"] = "FAILED"
        assert not verify_signature(payload, sig)

    def test_wrong_secret_rejected(self):
        payload = {"requestNo": "REQ-001", "status": "SUCCESS"}
        sig = sign_payload(payload, "correct-secret")
        assert not verify_signature(payload, sig, "wrong-secret")

    def test_empty_payload(self):
        payload = {}
        sig = sign_payload(payload)
        assert verify_signature(payload, sig)

    def test_different_payloads_different_sigs(self):
        sig1 = sign_payload({"a": 1})
        sig2 = sign_payload({"a": 2})
        assert sig1 != sig2

    def test_deterministic(self):
        payload = {"foo": "bar"}
        assert sign_payload(payload) == sign_payload(payload)

    def test_unicode_payload(self):
        payload = {"message": "盖章完成", "system": "VP"}
        sig = sign_payload(payload)
        assert verify_signature(payload, sig)
