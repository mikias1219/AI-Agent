from personal_agent.config.settings import Settings
from personal_agent.presentation.web.app import (
    _allowed_browser_origins,
    _configured_frontend_origins,
    _origin_allowed,
)


def test_configured_frontend_origins_splits_csv():
    settings = Settings()
    settings.frontend_origin = (
        "https://personal-ai-agent.vercel.app, https://personal-ai-agent-mikias-projects-608aa59d.vercel.app/"
    )
    assert _configured_frontend_origins(settings) == {
        "https://personal-ai-agent.vercel.app",
        "https://personal-ai-agent-mikias-projects-608aa59d.vercel.app",
    }


def test_allowed_browser_origins_includes_local_and_configured():
    settings = Settings()
    settings.frontend_origin = "https://personal-ai-agent.vercel.app"
    origins = _allowed_browser_origins(settings)
    assert "http://127.0.0.1:5173" in origins
    assert "https://personal-ai-agent.vercel.app" in origins


def test_origin_allowed_accepts_vercel_deploy_urls_in_production():
    allowed = {"https://personal-ai-agent.vercel.app"}
    assert _origin_allowed(
        "https://personal-ai-agent-p2pqoda2r-mikias-projects-608aa59d.vercel.app",
        allowed,
        production=True,
    )
    assert not _origin_allowed("https://other-app.vercel.app", allowed, production=True)
    assert not _origin_allowed(
        "https://personal-ai-agent.vercel.app.evil.com",
        allowed,
        production=True,
    )
    assert not _origin_allowed(
        "https://personal-ai-agent-p2pqoda2r-mikias-projects-608aa59d.vercel.app",
        allowed,
        production=False,
    )
