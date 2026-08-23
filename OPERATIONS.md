# Reflection Space — Operator Runbook

This document is for whoever is responsible for keeping Reflection Space
running during the pilot — even if that person did not build the
application. It complements `README.md` (which explains the code) by
focusing on what it takes to **run and look after** the app day to day.

## 1. What has to be true before the app will start

Reflection Space is a Streamlit app. On Streamlit Community Cloud (the
platform it is written for), these values are entered once under
**App settings → Secrets**, in `KEY = "value"` format, not committed to
GitHub.

### Required for the app to work at all

| Setting | What it's for | What happens if it's missing |
|---|---|---|
| `DATABASE_URL` | Connection string for the PostgreSQL database (accounts, reflections, logs) | The app cannot start meaningfully — nearly everything depends on the database |
| `ANTHROPIC_API_KEY` | Powers the AI reflection companion and Knowledge Assistant | Reflection generation and the Knowledge Assistant fail with a plain-language error; the rest of the app still works |

### Optional — the app degrades gracefully without these

| Setting | What it's for | What happens if it's missing |
|---|---|---|
| `GEMINI_API_KEY` | Turns reflections into search vectors for "similar past case" search | Semantic search is automatically disabled; the app falls back to a simpler recency-based view. Nothing breaks. |
| `QDRANT_URL` / `QDRANT_API_KEY` | Where those search vectors are stored | Same as above — semantic search quietly turns itself off |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `ALERT_EMAIL_TO` | Sends an email to an administrator when something breaks | No email alerts go out. Errors are still recorded inside the app's own Error Log screen. |
| `ADMIN_PASSWORD` | Left over from an earlier design | Not used anywhere in the current code. Safe to leave unset — see note in Section 6. |

Every tuning knob (rate limits, timeouts, pool size, session length,
etc.) has a safe built-in default and only needs to be touched if a
specific, observed problem calls for it — see the comments directly
above each one in `config.py`.

## 2. Deploying / redeploying

1. Push the change to the `main` branch on GitHub.
2. GitHub Actions automatically runs the full automated test suite
   (`.github/workflows/reliability-tests.yml` and
   `.github/workflows/security-tests.yml`). Wait for both to show a
   green check before treating the change as safe.
3. If the app is hosted on Streamlit Community Cloud connected to this
   repository, it redeploys itself automatically after a push to
   `main`. No manual deployment step is required.
4. On startup, the app automatically creates any database tables it
   needs if they don't already exist (`services/db_schema.py`). This
   is safe to run every time — it never deletes or overwrites existing
   data, and it's designed to be a no-op after the first run.

There is no separate "build step," Docker image, or manual database
migration to run by hand.

## 3. How to tell if something is wrong

Reflection Space has its own built-in Error Log, visible to System
Administrators inside the app (System Administration → Error Log). For
every problem it records:

- A plain-language description of what broke and where
- A stable reference number (the same number every time the same
  underlying problem happens again, so ten occurrences of one bug show
  up as one tracked issue, not ten)
- The full technical detail (exception type, message, traceback) in a
  format that can be copy-pasted straight to an AI assistant for
  diagnosis — you do not need to read or understand the traceback
  yourself
- If email alerting is configured (Section 1), a notification email is
  sent automatically when a new issue first appears

No case content, client names, or reflection text is ever written into
this log — only technical/operational information.

If the database itself is unreachable, the app cannot write to this
log at all; in that case, look at the platform's own logs (on
Streamlit Community Cloud: **Manage app → logs**).

## 4. Health checks

Reflection Space does not have a custom `/health` endpoint of its own.
For the pilot's scale, this is adequate because:

- Streamlit Community Cloud already restarts the app automatically if
  the process itself crashes (this covers "is the app alive at all").
- Whether the app can actually serve users correctly (database
  reachable, AI provider reachable) is answered every time someone
  loads a page — a broken dependency shows up immediately as a plain
  error message to the next person who uses that feature, and is
  simultaneously written to the Error Log described above.

If the pilot grows well beyond "hundreds of practitioners," a
dedicated readiness endpoint would be worth adding — not needed now.

## 5. Backup and recovery

**What Reflection Space itself is responsible for:** correctly writing
data to PostgreSQL and Qdrant, and correctly handling deletion. It does
not run its own backup jobs — that is the hosting platform's job.

**What you are responsible for confirming, outside this repository:**

- **PostgreSQL (Neon):** Neon takes automatic backups/point-in-time
  recovery on its own paid plans. Confirm the plan in use actually
  includes this, and know how to trigger a restore from Neon's own
  dashboard before the pilot starts — this repository cannot do that
  for you.
- **Qdrant:** holds only search vectors, never the system of record.
  If it is ever lost or corrupted, it can be rebuilt from PostgreSQL
  (the source of truth) by re-embedding existing reflections — there
  is no case data that exists only in Qdrant.
- **Recovery after a bad deploy:** because Streamlit Cloud deploys
  straight from GitHub, "roll back" means reverting to a previous
  commit on `main` and letting it redeploy — no separate release
  artifact to manage.

**Interaction with privacy:** deleted cases are held for
`DELETION_WINDOW_HOURS` (48 hours by default) before permanent purge,
specifically so a mistaken deletion can be undone. If your database
backup retention window is longer than that, a deleted case could
technically still exist inside an old backup after it's been purged
from the live app — this is a normal, expected trade-off of having
backups at all, but it's worth being aware of if a strict "deleted
means truly gone everywhere, immediately" requirement ever applies.

## 6. Known, accepted loose ends

- `ADMIN_PASSWORD` in `config.py` is not read by any other file in the
  application. It appears to be left over from an earlier design, from
  before per-user login (bcrypt-hashed, one account per person) was
  built. It is harmless to leave unset. Removing it entirely was
  judged not worth the (small) risk of touching working configuration
  during this final phase — flagged here so nobody spends time trying
  to figure out what it does.
- The Error Log's individual "occurrence" rows are never automatically
  pruned (grouped issues are deduplicated for display, but every raw
  occurrence is still stored). At pilot scale (hundreds of users) this
  is not a practical concern; if the app is still running unattended
  a year or more from now, a periodic cleanup of old, resolved
  occurrence rows would be a sensible addition.
