"""Unit tests for `app/util.py`.

Ids and timestamps are load-bearing: ids are the system's identity (names are
display-only, per the web contract), and list ordering is done by comparing the
ISO timestamp *strings*, so their format has to sort chronologically.
"""

from datetime import datetime, timedelta, timezone

from app.util import new_id, now_iso


class TestNewId:
    def test_uses_the_given_prefix(self):
        assert new_id("prj").startswith("prj_")
        assert new_id("dsn").startswith("dsn_")
        assert new_id("mod").startswith("mod_")

    def test_is_opaque_hex_suffix(self):
        suffix = new_id("prj").split("_", 1)[1]
        assert len(suffix) == 8
        assert all(c in "0123456789abcdef" for c in suffix)

    def test_ids_are_unique(self):
        """Ids are the identity across subsystems, so they must never repeat."""
        ids = {new_id("mod") for _ in range(5000)}
        assert len(ids) == 5000

    def test_url_safe(self):
        """Ids travel in path segments (`/api/designs/{id}`)."""
        ident = new_id("dsn")
        assert ident == ident.strip()
        assert "/" not in ident and "?" not in ident and " " not in ident


class TestNowIso:
    def test_is_parseable_iso_8601(self):
        parsed = datetime.fromisoformat(now_iso())
        assert parsed.tzinfo is not None

    def test_is_utc(self):
        assert datetime.fromisoformat(now_iso()).utcoffset() == timedelta(0)

    def test_is_current(self):
        delta = datetime.now(timezone.utc) - datetime.fromisoformat(now_iso())
        assert abs(delta) < timedelta(seconds=5)

    def test_sorts_lexicographically_in_chronological_order(self):
        """`ORDER BY created_time DESC` is a *string* comparison in SQLite, so a
        later timestamp must also be the larger string."""
        stamps = [now_iso() for _ in range(50)]
        assert stamps == sorted(stamps)
