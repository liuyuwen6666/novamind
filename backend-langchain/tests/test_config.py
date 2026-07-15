from app.core.config import get_settings

def test_settings_load():
    settings = get_settings()
    assert settings.APP_NAME == "NovaMind-LangChain"
    assert settings.DATABASE_URL is not None
