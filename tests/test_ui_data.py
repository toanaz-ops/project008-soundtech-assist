"""Non-Qt scene views backing the new pages."""

from wing_parser.ui.data import (
    channel_detail_rows,
    channel_rows,
    routing_view,
    summarize,
)


def test_summarize_counts_a_real_scene(vu_path):
    from wing_parser import WingScene

    info = summarize(WingScene.load(vu_path))
    assert info["counts"]["channels"] > 0
    assert info["counts"]["mains"] >= 1
    assert isinstance(info["live"], int)
    assert info["named"] <= info["counts"]["channels"]
    assert isinstance(info["anomalies"], int)


def test_channel_rows_are_ordered_and_typed(vu_path):
    from wing_parser import WingScene

    rows = channel_rows(WingScene.load(vu_path))
    assert rows
    numbers = [row.number for row in rows]
    assert numbers == sorted(numbers)
    assert all(isinstance(row.kind, str) for row in rows)


def test_channel_detail_pairs_cover_the_cli_fields(vu_path):
    from wing_parser import WingScene

    scene = WingScene.load(vu_path)
    pairs = dict(channel_detail_rows(scene.channel(1)))
    assert "Fader" in pairs
    assert "Type" in pairs


def test_routing_view_pairs_and_unclassified(vu_path):
    from wing_parser import WingScene

    pairs, unclassified = routing_view(WingScene.load(vu_path))
    assert any(label == "Live channels" for label, _ in pairs)
    assert isinstance(unclassified, list)
