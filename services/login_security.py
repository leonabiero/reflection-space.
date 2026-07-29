"""
Password hashing for login (services/identity.py).
==========================================================

Security hardening pass -- "Password hashing" change.

BEFORE this change, every professional's password was stored in plain
text in Streamlit Cloud Secrets (secrets.toml), and login checked it
with a simple `==` string comparison. That means:

  - Anyone who can view the app's Secrets (anyone with access to the
    Streamlit Cloud dashboard for this app, or a copy of secrets.toml)
    can read every professional's real password in plain text.
  - Because many people reuse passwords across systems, a leak of this
    app's secrets could expose a professional's password for OTHER,
    unrelated accounts too.

AFTER this change, secrets.toml stores a bcrypt HASH of each password
instead of the password itself -- something that is computationally
infeasible to reverse back into the original password, even for
someone who can see it directly. Logging in still works exactly the
same way for the person typing their password; only what's stored on
disk (in Secrets) changes.

This means every existing account's `password = "..."` entry in
secrets.toml must be replaced with a hash before this change is
deployed -- see generate_password_hash.py (project root) for a small
script that turns a plain-text password into the hash string to paste
into Secrets. Until an account's password is replaced with a hash,
that account will no longer be able to log in (see the migration
notes below).

Why bcrypt
----------
bcrypt is a purpose-built password-hashing algorithm (not a general
hash like SHA-256/MD5): it is deliberately slow, includes a random
"salt" baked into every hash automatically (so two people with the
same password get completely different-looking hashes, and
pre-computed "rainbow table" attacks don't work), and has a
multi-decade track record for exactly this job. Comparing a candidate
password against a stored hash is also intrinsically constant-time
(the underlying C implementation does not short-circuit on the first
mismatched byte the way a plain `==` string comparison can), which
closes off password-guessing via response-time measurement too.
"""

import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Turn a plain-text password into a bcrypt hash string, suitable for
    pasting into secrets.toml as the `password` value for an account.

    Used by generate_password_hash.py (the one-off admin tool for
    creating/rotating an account's password) -- not used during normal
    login itself.
    """
    if not plain_password:
        raise ValueError("Password must not be empty.")
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Check a password typed at login against the bcrypt hash stored for
    that account in secrets.toml. Returns False (never raises) for any
    malformed/legacy/missing hash, so a bad or not-yet-migrated entry
    in secrets.toml simply fails closed as "wrong password" rather
    than crashing the login page.
    """
    if not plain_password or not stored_hash:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            stored_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Raised by bcrypt if stored_hash isn't a valid bcrypt hash at
        # all -- e.g. an account that still has an old plain-text
        # password in secrets.toml and hasn't been migrated yet.
        return False


def looks_like_bcrypt_hash(value: str) -> bool:
    """
    True if `value` looks like a bcrypt hash (starts with one of
    bcrypt's version prefixes and is the expected length) rather than
    a plain-text password. Used only to give a clearer, more specific
    error/log message when an account in secrets.toml hasn't been
    migrated yet -- never used as the actual security check (that's
    always verify_password() above).
    """
    if not value:
        return False
    return value.startswith(("$2a$", "$2b$", "$2y$")) and len(value) == 60