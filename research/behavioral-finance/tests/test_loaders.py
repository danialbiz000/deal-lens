"""Network-free tests for the NSE rename-merge logic in data/loaders.py.

The README's "Empirical results" section rests on this merge map being
correct (no symbol lost, no symbol double-counted) -- these tests don't hit
the network, they just lock in the map's internal consistency.
"""
from __future__ import annotations

from data.loaders import _NSE_RENAME_CHAINS, _nse_symbol_merge_map


def test_every_raw_symbol_appears_in_exactly_one_chain():
    seen = []
    for chain in _NSE_RENAME_CHAINS:
        seen.extend(chain)
    assert len(seen) == len(set(seen)), "a raw symbol appears in more than one rename chain"


def test_merge_map_points_every_symbol_to_its_chains_final_name():
    mapping = _nse_symbol_merge_map()
    for chain in _NSE_RENAME_CHAINS:
        canonical = chain[-1]
        for symbol in chain:
            assert mapping[symbol] == canonical
        # the canonical name must map to itself
        assert mapping[canonical] == canonical


def test_hdfc_and_hdfcbank_are_not_merged():
    """Regression guard for the specific judgment call documented in
    README.md: HDFC (housing finance) and HDFCBANK were separate listed
    companies for this entire sample and must never end up in the same
    rename chain."""
    for chain in _NSE_RENAME_CHAINS:
        assert not ({"HDFC", "HDFCBANK"} <= set(chain))
