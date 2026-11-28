from app.services.visual_assets import VisualAssetStore


def test_visual_asset_paths_are_isolated_by_user_and_note(tmp_path):
    png = b"\x89PNG\r\n\x1a\nvisual"
    store = VisualAssetStore(tmp_path)

    first = store.save("u1", "note1", 1, png)
    second = store.save("u2", "note1", 1, png)

    assert first.path != second.path
    assert first.path.read_bytes() == png
    assert second.path.read_bytes() == png
