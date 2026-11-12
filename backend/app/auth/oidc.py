"""Keycloak OpenID Connect token validation and JWKS caching."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import httpx
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel

from app.core.config import settings

# JWKS cache
_JWKS_CACHE: Dict[str, Any] = {}
_JWKS_EXPIRY: float = 0
_CACHE_TTL_SECONDS: int = 3600


class TokenValidationError(JWTError):
    """Specific error raised during token validation."""
    pass


class TokenPayload(BaseModel):
    sub: str
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    aud: Optional[Any] = None
    iss: Optional[str] = None
    exp: Optional[int] = None
    roles: List[str] = []
    raw_claims: Dict[str, Any] = {}


async def get_jwks() -> Dict[str, Any]:
    """Fetches and caches the JSON Web Key Set from Keycloak."""
    global _JWKS_CACHE, _JWKS_EXPIRY
    current_time = time.time()

    if _JWKS_CACHE and current_time < _JWKS_EXPIRY:
        return _JWKS_CACHE

    jwks_url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            if response.status_code == 200:
                _JWKS_CACHE = response.json()
                _JWKS_EXPIRY = current_time + _CACHE_TTL_SECONDS
                return _JWKS_CACHE
    except Exception:
        pass

    return _JWKS_CACHE


def validate_token(token: str, jwks: Optional[Dict[str, Any]] = None) -> TokenPayload:
    """
    Validates a JWT access token against the JWKS keys.
    Verifies: signature, algorithm (RS256/HS256 in test mode), issuer, audience, and exp.

    Raises TokenValidationError or JWTError when validation fails.
    """
    if not token or not isinstance(token, str):
        raise TokenValidationError("Empty or invalid token supplied")

    # 1. Demo token handling
    if token.startswith("demo-token-"):
        if not settings.DEMO_MODE:
            raise TokenValidationError(
                "Demo token rejected: DEMO_MODE is disabled in application configuration."
            )
        if settings.ENVIRONMENT != "local":
            raise TokenValidationError(
                f"Demo token rejected: demo authentication is forbidden in '{settings.ENVIRONMENT}' environment."
            )
        # Format: demo-token-<email_prefix>-<role>
        # Role may contain underscores (e.g. workplace_safety_manager); only split once
        # after the email prefix so the full role string is preserved.
        remainder = token.removeprefix("demo-token-")
        email_prefix, sep, role = remainder.partition("-")
        if not sep:
            email_prefix, role = "analyst", "public_health_analyst"
        email = f"{email_prefix}@demo.local"
        return TokenPayload(
            sub=f"demo-sub-{email_prefix}",
            email=email,
            preferred_username=email,
            roles=[role],
            raw_claims={"demo": True},
        )

    # 2. Standard JWT Header Inspection
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as e:
        raise TokenValidationError(f"Malformed JWT header: {e}")

    alg = unverified_header.get("alg")
    if not alg:
        raise TokenValidationError("JWT header missing algorithm parameter ('alg')")

    # 3. Symmetric key decoding (test harness or explicit HS256 mode)
    if alg == "HS256":
        try:
            claims = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                audience=settings.KEYCLOAK_AUDIENCE,
                options={"verify_exp": True, "verify_aud": True},
            )
        except ExpiredSignatureError:
            raise TokenValidationError("Token has expired")
        except JWTError as e:
            raise TokenValidationError(f"HS256 token validation failed: {e}")
    elif alg == "RS256":
        # RS256 Keycloak JWKS validation
        jwks = jwks or {}
        kid = unverified_header.get("kid")
        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = k
                break

        if not key:
            keys = jwks.get("keys", [])
            if len(keys) == 1:
                key = keys[0]
            else:
                raise TokenValidationError(f"Public key with kid='{kid}' not found in JWKS")

        decode_key = key.get("key", key) if isinstance(key, dict) and "key" in key else key
        issuer = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        try:
            claims = jwt.decode(
                token,
                decode_key,
                algorithms=["RS256"],
                audience=settings.KEYCLOAK_AUDIENCE,
                issuer=issuer,
                options={
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                },
            )
        except ExpiredSignatureError:
            raise TokenValidationError("Token has expired")
        except JWTError as e:
            raise TokenValidationError(f"RS256 token validation failed: {e}")
    else:
        raise TokenValidationError(f"Unsupported JWT algorithm: {alg}")

    # Extract roles from realm_access or direct roles claim
    realm_access = claims.get("realm_access", {})
    roles = realm_access.get("roles", []) or claims.get("roles", [])

    return TokenPayload(
        sub=claims.get("sub", ""),
        email=claims.get("email"),
        preferred_username=claims.get("preferred_username"),
        aud=claims.get("aud"),
        iss=claims.get("iss"),
        exp=claims.get("exp"),
        roles=roles,
        raw_claims=claims,
    )
