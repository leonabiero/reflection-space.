"""
RAG Logging
=============

Shared, centralized logging helper for the Hybrid RAG development trace
(the "[RAG] ..." lines previously produced by several independent,
ad-hoc `_log()` helpers scattered across services/qdrant_service.py,
rdi/retrieval_service.py, rdi/context_engine.py, and
rdi/reflection_context.py).

Why this module exists
------------------------
Those ad-hoc helpers all did roughly:

    def _log(msg):
        try:
            print(f"[RAG] {msg}")
        except Exception:
            pass

That *looks* correct, but on a hosted container process (like Streamlit
Cloud), stdout is usually NOT attached to a real terminal. When that's
the case, CPython switches stdout from line-buffered to fully
block-buffered -- print() output just queues into an internal buffer and
is only actually written out once that buffer fills or the process
exits. Combined with Streamlit's frequent reruns, this meant "[RAG]"
lines could sit unflushed for a long time, or effectively never show up
in the Streamlit Cloud log viewer, even though the code was executing
exactly as intended.

This module fixes that two ways, deliberately redundant so a change on
either side (Python's buffering behavior, or Streamlit Cloud's log
capture) can't silently break tracing again:

    1. A real `logging.Logger` ("rag"), with its own StreamHandler bound
       directly to sys.stdout, level INFO, and propagate=False -- so it
       can never be filtered or muted by whatever level Streamlit's own
       root/"streamlit" logger happens to be configured at.
    2. A plain print(..., flush=True) as a fallback -- flush=True forces
       an immediate OS-level write instead of waiting on the buffer, so
       even in the (unlikely) case the logging handler is ever removed
       or misconfigured, this print alone is still reliable.

Importing this module has the side effect of initializing the logger
and emitting one confirmation line:

    [RAG] Logging initialized successfully

immediately, the first time it's imported in a given Streamlit Cloud
process (Streamlit's multipage apps only run the ONE script the user
navigated to, not app.py, so this module is written to self-initialize
on import rather than depending on app.py being the entry point).
"""

import logging
import sys

_logger = None


def get_rag_logger():
    """Return the shared "rag" logger, creating and configuring it on
    first call. Idempotent -- safe to call many times; the underlying
    logging.Logger + handler are only ever created once per process."""
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("rag")
    logger.setLevel(logging.INFO)
    # Never hand records up to the root/"streamlit" logger -- that logger
    # may be configured at a different level (e.g. WARNING) by Streamlit
    # itself, which would otherwise silently drop our INFO-level lines.
    logger.propagate = False

    # Defensive: if this module were ever re-imported in a way that
    # re-ran this function (shouldn't happen given the _logger guard
    # above, but kept cheap and safe), don't stack duplicate handlers.
    for existing_handler in list(logger.handlers):
        logger.removeHandler(existing_handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    _logger = logger
    return logger


def rag_log(msg):
    """Primary logging entry point for the whole Hybrid RAG pipeline.
    Replaces every previous ad-hoc `_log()` helper.

    Writes through the configured `logging.Logger` (handler bound to
    sys.stdout, INFO level, non-propagating -- logging.StreamHandler
    flushes its stream after every emit() call by default, so this
    alone is enough to avoid the stdout-buffering problem that caused
    lines to go missing before). Only if that fails for any reason does
    this fall back to a directly flushed print() -- deliberately NOT run
    unconditionally alongside the logger, so a healthy logger never
    prints each line twice. Never raises -- a logging failure must never
    break the page it's called from.
    """
    try:
        get_rag_logger().info(msg)
        return
    except Exception:
        pass
    try:
        print(msg, flush=True)
    except Exception:
        pass


# Self-initialize + emit the startup confirmation line the moment this
# module is first imported anywhere in the app (documentation.py,
# reflection_space.py, growth_dashboard.py, etc. all eventually import
# a module that imports this one). Guarded by the _logger is-None check
# inside get_rag_logger(), so this only actually logs once per process,
# not once per page load/rerun.
if _logger is None:
    rag_log("[RAG] Logging initialized successfully")