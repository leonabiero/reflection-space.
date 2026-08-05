"""
Browser Cookie for Persistent Login (services/identity.py)
================================================================

Companion to services/session_store.py: that module is the
server-side source of truth ("is this session_id still valid, and who
does it belong to"); this module is purely the mechanics of getting
that session_id into, and out