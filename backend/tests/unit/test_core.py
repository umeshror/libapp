def test_app_starts():
    from app.main import app

    assert app is not None


def test_settings_loaded():
    from app.core.config import settings

    assert settings.DATABASE_URL is not None
