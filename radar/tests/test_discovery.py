"""relevance filtering shared by every discovery monitor.

momo and eslite both do fuzzy keyword search, not exact matching, so a scan
for "戰鬥陀螺" pulls in unrelated toys and books. looks_relevant() is the one
gate both monitors call before accepting a hit.
"""

from __future__ import annotations

from monitors.discovery import looks_relevant


def test_accepts_names_with_spinner_words_or_model_codes():
    assert looks_relevant("【TAKARA TOMY】BEYBLADE X 戰鬥陀螺X UX-15 鮫鯊狂鱗改造組")
    assert looks_relevant("戰鬥紙陀螺: 只要3張紙, 我的帥氣陀螺就誕生了!")
    assert looks_relevant("Beyblade X starter set")
    assert looks_relevant("陀螺X 5-70DB 3-80S")  # model absent but has 陀螺


def test_rejects_unrelated_hits_pulled_in_by_fuzzy_search():
    assert not looks_relevant("【BAKUGAN 爆丸】爆丸戰鬥場(新款爆丸)")
    assert not looks_relevant("【ONE HOUSE】享樂趣加大貨櫃公仔盒 4入")
    assert not looks_relevant("數感小學冒險系列 1-6: 數字的謎團 (6冊合售)")


def test_empty_or_missing_name_is_not_relevant():
    assert not looks_relevant("")
    assert not looks_relevant(None)  # type: ignore[arg-type]
