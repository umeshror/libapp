def test_app_starts():
    from app.main import app

    assert app is not None


def test_settings_loaded():
    from app.core.config import settings

    assert settings.SQLALCHEMY_DATABASE_URI is not None
