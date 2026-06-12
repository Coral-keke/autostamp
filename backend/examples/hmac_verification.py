"""
HMAC Signature Verification — for callback receivers.

Auto-Stamp sends callbacks with an HMAC-SHA256 signature in the
X-Stamp-Signature header. Receiving systems should verify this
to ensure the callback genuinely came from Auto-Stamp.

Header format:
  X-Stamp-Signature: sha256=<hex-encoded-hmac>
  X-Stamp-RequestNo: <requestNo>

The signature covers the raw JSON request body.
"""
import hashlib
import hmac
from fastapi import Request, HTTPException


async def verify_stamp_callback(request: Request, secret: str):
    """
    Verify that an incoming callback from Auto-Stamp has a valid HMAC signature.

    Usage in FastAPI:
        @app.post("/api/seal/callback")
        async def handle_callback(request: Request):
            await verify_stamp_callback(request, secret="shared-secret")
            body = await request.json()
            # ... process callback ...

    Raises:
        HTTPException(401) if signature is missing or invalid.
    """
    signature_header = request.headers.get("X-Stamp-Signature", "")
    if not signature_header:
        raise HTTPException(401, "Missing X-Stamp-Signature header")

    # Parse "sha256=<hex>"
    if not signature_header.startswith("sha256="):
        raise HTTPException(401, "Invalid signature format")
    expected_sig = signature_header[7:]  # strip "sha256="

    # Read body (must be raw bytes)
    body_bytes = await request.body()

    # Compute HMAC
    computed = hmac.new(
        secret.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed, expected_sig):
        raise HTTPException(401, "Signature mismatch")


# ── Standalone verification (non-FastAPI) ──────────────────

def verify_signature(body: str | bytes, signature_header: str, secret: str) -> bool:
    """
    Verify HMAC signature without FastAPI dependency.

    Args:
        body: Raw request body (string or bytes).
        signature_header: Value of X-Stamp-Signature header (e.g. "sha256=abc123...").
        secret: Shared HMAC secret.

    Returns:
        True if signature is valid.
    """
    if not signature_header.startswith("sha256="):
        return False

    expected = signature_header[7:]
    if isinstance(body, str):
        body = body.encode()

    computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)


# ── Flask example ──────────────────────────────────────────

# @app.route("/api/seal/callback", methods=["POST"])
# def handle_callback():
#     signature = request.headers.get("X-Stamp-Signature", "")
#     body = request.get_data()  # raw bytes
#     if not verify_signature(body, signature, SECRET):
#         return {"error": "Invalid signature"}, 401
#     data = request.get_json()
#     # ... process callback ...
#     return {"status": "ok"}


# ── Java / Spring Boot example ─────────────────────────────

# @PostMapping("/api/seal/callback")
# public ResponseEntity<?> handleCallback(
#     @RequestHeader("X-Stamp-Signature") String signature,
#     @RequestBody String body) {
#
#     Mac mac = Mac.getInstance("HmacSHA256");
#     mac.init(new SecretKeySpec(SECRET.getBytes(), "HmacSHA256"));
#     byte[] computed = mac.doFinal(body.getBytes());
#     String computedHex = HexFormat.of().formatHex(computed);
#
#     String expected = signature.replace("sha256=", "");
#     if (!MessageDigest.isEqual(computedHex.getBytes(), expected.getBytes())) {
#         return ResponseEntity.status(401).body("Invalid signature");
#     }
#     // ... process callback ...
# }
