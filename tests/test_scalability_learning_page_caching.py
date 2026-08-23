"""
Phase 3 -- safe-caching regression coverage for pages/learning.py.

pages/learning.py is a Streamlit page script (it renders UI at import
time), so -- consistent with the rest of this test suite, which tests
the services/*.py layer rather than importing pages/*.py directly --
these tests check the two things that actually matter for caching
safety without needing a full Streamlit page-rendering context:

1. The three functions pages/learning.py caches with st.cache_data are
   still, at the SERVICE layer, genuinely organisation-wide/anonymous
   with no per-user or per-session argument. If a future change ever
   adds a user-identifying parameter to one of these functions without
   also updating the caching in pages/learning.py, that would risk one
   manager's cached view being served to another manager -- this test
   fails loudly if that ever happens.

2. pages/learning.py's source still wires the caching up the way this
   Phase 3 pass intended (cache_data, not cache_resource; the expected
   TTLs), so an accidental revert or edit is caught here rather than
   only being noticed in production.
"""

import inspect
import re
import unittest
from pathlib import Path

from services.presence import get_active_social_workers
from services.reflection_log import get_recent_theme_counts
from services.exploration_log import get_aggregated_theme_counts


class TestCachedFunctionsHaveNoUserIdentifyingParameter(unittest.TestCase):

    def test_active_social_workers_has_no_user_identifying_parameter(self):
        """
        Team Presence is cached and shared across every manager's
        session (see pages/learning.py). That is only safe because
        this function takes no argument that could scope its result
        to one particular caller -- it always returns the same
        organisation-wide answer no matter who calls it.
        """
        params = inspect.signature(get_active_social_workers).parameters
        self.assertEqual(
            dict(params), {},
            "get_active_social_workers() gained a parameter -- re-check whether "
            "pages/learning.py's cached wrapper is still safe to share across sessions.",
        )

    def test_recent_theme_counts_only_takes_a_shared_limit_parameter(self):
        """
        Cached and shared across sessions in pages/learning.py. Must
        only ever take `limit` (an organisation-wide window size),
        never anything identifying a specific professional or case.
        """
        params = set(inspect.signature(get_recent_theme_counts).parameters)
        self.assertEqual(
            params, {"limit"},
            f"get_recent_theme_counts() parameters changed to {params} -- re-check whether "
            f"pages/learning.py's cached wrapper is still safe to share across sessions.",
        )

    def test_aggregated_theme_counts_only_takes_a_shared_since_parameter(self):
        """
        Cached and shared across sessions in pages/learning.py. Must
        only ever take `since_iso` (an organisation-wide date cutoff),
        never anything identifying a specific professional or case.
        """
        params = set(inspect.signature(get_aggregated_theme_counts).parameters)
        self.assertEqual(
            params, {"since_iso"},
            f"get_aggregated_theme_counts() parameters changed to {params} -- re-check whether "
            f"pages/learning.py's cached wrapper is still safe to share across sessions.",
        )


class TestLearningPageCachingIsWiredCorrectly(unittest.TestCase):

    def test_expected_safe_ttls_and_cache_type(self):
        """
        Confirms pages/learning.py still uses st.cache_data (never
        st.cache_resource, which is meant for shared objects/
        connections, not per-call results) with the specific short
        TTLs this Phase 3 pass chose: 15s for near-real-time presence,
        60s for the recent themes tally, 300s for the more expensive
        6-month aggregate.
        """
        source = Path("pages/learning.py").read_text(encoding="utf-8")

        self.assertNotIn(
            "st.cache_resource", source,
            "pages/learning.py should not use st.cache_resource for these three "
            "per-call, organisation-wide results -- st.cache_data is the correct tool.",
        )

        expected = {
            "_cached_active_social_workers": 15,
            "_cached_recent_theme_counts": 60,
            "_cached_aggregated_theme_counts": 300,
        }
        for func_name, ttl in expected.items():
            pattern = rf"@st\.cache_data\(ttl={ttl}\)\s*\ndef {func_name}\("
            self.assertRegex(
                source, pattern,
                f"Expected to find {func_name}() decorated with @st.cache_data(ttl={ttl}) "
                f"in pages/learning.py -- the caching may have been changed or removed.",
            )


if __name__ == "__main__":
    unittest.main()
