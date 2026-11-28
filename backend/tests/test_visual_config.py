from app.core.config import settings


def test_visual_evidence_defaults_to_disabled():
    enabled = getattr(settings, "VISUAL_EVIDENCE_ENABLED", None)
    assert enabled is False


def test_visual_max_pages_defaults_to_three():
    limit = getattr(settings, "VISUAL_MAX_PAGES_PER_DOC", None)
    assert limit == 3


def test_visual_asset_dir_defaults_to_data_directory():
    path = getattr(settings, "VISUAL_ASSET_DIR", None)
    assert path == "./data/import_assets"


def test_visual_model_defaults_to_deepseek_flash():
    model = getattr(settings, "VISUAL_MODEL", None)
    assert model == "deepseek-v4-flash"


def test_visual_timeout_defaults_to_120_seconds():
    timeout = getattr(settings, "VISUAL_TIMEOUT", None)
    assert timeout == 120
