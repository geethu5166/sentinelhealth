"""Unit tests for OpenID Connect token validation and demo mode enforcement."""

import time
import pytest
from jose import jwt, jwk
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.auth.oidc import TokenValidationError, validate_token
from app.core.config import Settings, settings


@pytest.fixture(scope="module")
def rsa_key_pair():
    """Generates an RSA key pair and standard JWK for testing RS256 JWT signatures."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    # Construct genuine RFC 7517 JWK
    key_dict = jwk.construct(public_pem, "RS256").to_dict()
    key_dict["kid"] = "key-2026-01"

    return private_pem, key_dict


def test_non_local_config_refuses_demo_mode():
    """Settings must raise ValueError if DEMO_MODE is True in non-local environments."""
    with pytest.raises(ValueError, match="strictly prohibited in 'production'"):
        Settings(
            ENVIRONMENT="production",
            DEMO_MODE=True,
        )

    with pytest.raises(ValueError, match="strictly prohibited in 'staging'"):
        Settings(
            ENVIRONMENT="staging",
            DEMO_MODE=True,
        )


def test_demo_token_preserves_underscored_role(monkeypatch):
    """Demo token role segment may contain underscores and must not be truncated."""
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")

    payload = validate_token("demo-token-safety-workplace_safety_manager")
    assert payload.email == "safety@demo.local"
    assert payload.roles == ["workplace_safety_manager"]
    assert payload.sub == "demo-sub-safety"


def test_demo_token_rejected_when_demo_mode_disabled(monkeypatch):
    """Demo tokens must be rejected when DEMO_MODE is False."""
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")

    with pytest.raises(TokenValidationError, match="DEMO_MODE is disabled"):
        validate_token("demo-token-analyst-public_health_analyst")


def test_demo_token_rejected_in_non_local_environment(monkeypatch):
    """Demo tokens must be rejected if environment is not local."""
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    with pytest.raises(TokenValidationError, match="forbidden in 'production'"):
        validate_token("demo-token-analyst-public_health_analyst")


def test_valid_rs256_token_accepted(rsa_key_pair, monkeypatch):
    """A properly signed RS256 token matching JWKS, issuer, and audience must succeed."""
    private_pem, key_dict = rsa_key_pair
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "http://keycloak.example.com")
    monkeypatch.setattr(settings, "KEYCLOAK_REALM", "sentinel-prod")
    monkeypatch.setattr(settings, "KEYCLOAK_AUDIENCE", "sentinel-api")

    issuer = "http://keycloak.example.com/realms/sentinel-prod"
    now = int(time.time())

    claims = {
        "sub": "keycloak-user-uuid-1234",
        "email": "epidemiologist@health.gov",
        "preferred_username": "dr.epidem",
        "iss": issuer,
        "aud": "sentinel-api",
        "exp": now + 3600,
        "iat": now,
        "realm_access": {
            "roles": ["public_health_analyst"]
        },
    }

    token = jwt.encode(
        claims,
        private_pem,
        algorithm="RS256",
        headers={"kid": "key-2026-01"},
    )

    mock_jwks = {"keys": [key_dict]}

    payload = validate_token(token, jwks=mock_jwks)
    assert payload.sub == "keycloak-user-uuid-1234"
    assert payload.email == "epidemiologist@health.gov"
    assert "public_health_analyst" in payload.roles


def test_rs256_expired_token_rejected(rsa_key_pair, monkeypatch):
    """Expired RS256 token must be rejected with TokenValidationError."""
    private_pem, key_dict = rsa_key_pair
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "http://keycloak.example.com")
    monkeypatch.setattr(settings, "KEYCLOAK_REALM", "sentinel-prod")
    monkeypatch.setattr(settings, "KEYCLOAK_AUDIENCE", "sentinel-api")

    issuer = "http://keycloak.example.com/realms/sentinel-prod"
    now = int(time.time())

    claims = {
        "sub": "user-expired",
        "iss": issuer,
        "aud": "sentinel-api",
        "exp": now - 300,  # Expired 5 minutes ago
        "iat": now - 3600,
    }

    token = jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "key-2026-01"})
    mock_jwks = {"keys": [key_dict]}

    with pytest.raises(TokenValidationError, match="expired"):
        validate_token(token, jwks=mock_jwks)


def test_rs256_wrong_issuer_rejected(rsa_key_pair, monkeypatch):
    """Token with mismatched issuer must be rejected."""
    private_pem, key_dict = rsa_key_pair
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "http://keycloak.example.com")
    monkeypatch.setattr(settings, "KEYCLOAK_REALM", "sentinel-prod")
    monkeypatch.setattr(settings, "KEYCLOAK_AUDIENCE", "sentinel-api")

    now = int(time.time())
    claims = {
        "sub": "user-bad-issuer",
        "iss": "http://rogue-idp.attacker.com/realms/evil",
        "aud": "sentinel-api",
        "exp": now + 3600,
    }

    token = jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "key-2026-01"})
    mock_jwks = {"keys": [key_dict]}

    with pytest.raises(TokenValidationError, match="failed"):
        validate_token(token, jwks=mock_jwks)


def test_rs256_wrong_audience_rejected(rsa_key_pair, monkeypatch):
    """Token with mismatched audience must be rejected."""
    private_pem, key_dict = rsa_key_pair
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "http://keycloak.example.com")
    monkeypatch.setattr(settings, "KEYCLOAK_REALM", "sentinel-prod")
    monkeypatch.setattr(settings, "KEYCLOAK_AUDIENCE", "sentinel-api")

    issuer = "http://keycloak.example.com/realms/sentinel-prod"
    now = int(time.time())
    claims = {
        "sub": "user-bad-aud",
        "iss": issuer,
        "aud": "some-other-service",
        "exp": now + 3600,
    }

    token = jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "key-2026-01"})
    mock_jwks = {"keys": [key_dict]}

    with pytest.raises(TokenValidationError, match="failed"):
        validate_token(token, jwks=mock_jwks)


def test_rs256_wrong_signature_rejected(rsa_key_pair, monkeypatch):
    """Token signed with a different private key must fail signature verification."""
    _, key_dict = rsa_key_pair
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "http://keycloak.example.com")
    monkeypatch.setattr(settings, "KEYCLOAK_REALM", "sentinel-prod")
    monkeypatch.setattr(settings, "KEYCLOAK_AUDIENCE", "sentinel-api")

    # Generate a rogue key
    rogue_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rogue_pem = rogue_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    issuer = "http://keycloak.example.com/realms/sentinel-prod"
    now = int(time.time())
    claims = {
        "sub": "user-forged",
        "iss": issuer,
        "aud": "sentinel-api",
        "exp": now + 3600,
    }

    token = jwt.encode(claims, rogue_pem, algorithm="RS256", headers={"kid": "key-2026-01"})
    mock_jwks = {"keys": [key_dict]}

    with pytest.raises(TokenValidationError, match="failed"):
        validate_token(token, jwks=mock_jwks)
