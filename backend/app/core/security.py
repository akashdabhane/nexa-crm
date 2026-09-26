"""Verification of Supabase-issued JWT access tokens."""

import jwt
from jwt import PyJWKClient

from app.core.config import settings

SUPABASE_AUDIENCE = "authenticated"
ASYMMETRIC_ALGORITHMS = {"RS256", "ES256"}

_jwks_client: PyJWKClient | None = None


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired or has a bad signature."""


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.supabase_url:
            raise TokenError("SUPABASE_URL is not configured")
        jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def decode_supabase_token(token: str) -> dict:
    """Verify signature, expiry and audience; return the token claims.

    Supabase projects sign tokens either with asymmetric keys (RS256/ES256,
    verified with the public JWKS) or with the legacy shared HS256 secret.
    """
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
        if algorithm == "HS256":
            if not settings.supabase_jwt_secret:
                raise TokenError("HS256 tokens require SUPABASE_JWT_SECRET")
            key = settings.supabase_jwt_secret
        elif algorithm in ASYMMETRIC_ALGORITHMS:
            key = _get_jwks_client().get_signing_key_from_jwt(token).key
        else:
            raise TokenError(f"Unsupported token algorithm: {algorithm}")

        return jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=SUPABASE_AUDIENCE,
            options={"require": ["exp", "sub"]},
        )
    except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
        raise TokenError(str(exc)) from exc
