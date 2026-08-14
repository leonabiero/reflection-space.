"""
_bootstrap.py
=============

What this file does, in plain English:

Every other file in this load_test/ folder needs to "borrow" real
pieces of the actual Reflection Space app (for example, the function
that saves a draft, or the function that submits a finished note) so
that our test uses the EXACT same code the real app uses -- not a
copy, not a guess.

For that borrowing to work, two things have to happen before
anything else runs:

  1. Python needs to be told "the main app's folder is over here" so
     that lines like `from services.draft_storage import save_draft`
     can find it. (This file is inside load_test/, one folder below
     the main app, so we add the parent folder to Python's search
     path.)

  2. The secret keys the app needs (database address, Gemini API key,
     Qdrant address) need to be loaded from your load_test/.env file
     into the environment, the same way they're loaded when the real
     app runs on Streamlit Cloud.

Every script in this folder starts with:

    import _bootstrap

...and that one line quietly does both of the above before anything
else in that script runs.
"""

import os
import sys

# Step 1: make the main app importable.
# This file lives at .../reflection-space/load_test/_bootstrap.py, so
# the main app's folder is one level up from here.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Step 2: load load_test/.env (your real secret keys, copied in by
# you -- see .env.example in this same folder for what's needed).
try:
    from dotenv import load_dotenv
    _ENV_PATH = os.path.join(_THIS_DIR, ".env")
    load_dotenv(_ENV_PATH)
except ImportError:
    print(
        "NOTE: the 'python-dotenv' helper isn't installed yet. "
        "Run: pip install -r load_test/requirements.txt --break-system-packages"
    )
    raise

# A friendly, early check: if the database address is missing, every
# script in this folder will fail in a confusing way later. Catch it
# here instead, with a clear plain-English message.
if not os.getenv("DATABASE_URL"):
    print(
        "\nSTOP: load_test/.env is missing DATABASE_URL (or the .env file "
        "doesn't exist yet).\n"
        "Copy load_test/.env.example to load_test/.env and fill in your "
        "real values (the same ones your main app uses) before running "
        "any test script.\n"
    )
    sys.exit(1)
