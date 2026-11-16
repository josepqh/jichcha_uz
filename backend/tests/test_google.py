from unittest import mock

import pytest

from apps.users import google

VALID = {"iss": "https://accounts.google.com", "email": "Ali@Gmail.com", "email_verified": True, "sub": "42"}


def verify_with(claims=None, error=None):
    with mock.patch.object(google.id_token, "verify_oauth2_token", return_value=claims, side_effect=error):
        return google.verify_credential("credential")


def test_valid_token_returns_lowercased_email():
    assert verify_with(VALID) == google.GoogleIdentity(email="ali@gmail.com", subject="42")


@pytest.mark.parametrize(
    "claims",
    [
        {**VALID, "iss": "https://evil.example"},
        {**VALID, "email_verified": False},
        {key: value for key, value in VALID.items() if key != "email"},
    ],
)
def test_rejects_untrusted_claims(claims):
    with pytest.raises(google.GoogleTokenError):
        verify_with(claims)


def test_signature_or_audience_failure():
    with pytest.raises(google.GoogleTokenError):
        verify_with(error=ValueError("Token has wrong audience"))
