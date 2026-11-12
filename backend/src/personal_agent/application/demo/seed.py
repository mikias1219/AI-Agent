"""Seed and reset the isolated demo database (UX-12)."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from personal_agent.app.container import AppContainer
from personal_agent.domain.models import OwnerProfile

logger = logging.getLogger(__name__)

DEMO_OWNER = "demo"
DEMO_MARKER = "demo.seeded"


def _sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite"):
        return None
    # sqlite:///./data/demo.db or sqlite:////abs/path
    raw = database_url.split(":///", 1)[-1]
    if raw.startswith("/") and not raw.startswith("//"):
        return Path(raw)
    parsed = urlparse(database_url)
    path = parsed.path or ""
    if path.startswith("/") and len(path) > 1 and path[2] == ":":  # windows-ish
        return Path(path)
    return Path(path.lstrip("/")) if path else None


def reset_demo_database(database_url: str) -> None:
    """Delete the demo SQLite file so the next build recreates a clean schema."""
    path = _sqlite_path(database_url)
    if path is None:
        raise ValueError("Demo reset requires a sqlite DEMO_DATABASE_URL.")
    if path.exists():
        path.unlink()
        logger.info("Removed demo database at %s", path)


def ensure_demo_seeded(container: AppContainer, *, force: bool = False) -> dict[str, object]:
    """Idempotently seed demo owner data. Returns a small summary."""
    audit = container.audit
    existing = audit.list_recent(limit=1, offset=0, events=[DEMO_MARKER])
    if existing and not force:
        return {"seeded": False, "owner": DEMO_OWNER}

    profiles = container.profiles
    profile = profiles.get(DEMO_OWNER)
    if not profile.name:
        profiles.save(
            OwnerProfile(
                owner_id=DEMO_OWNER,
                name="Demo Owner",
                timezone="UTC",
                language="en",
                wizard_completed=True,
            )
        )
    else:
        profiles.save(
            OwnerProfile(
                owner_id=DEMO_OWNER,
                name=profile.name or "Demo Owner",
                timezone=profile.timezone or "UTC",
                language=profile.language or "en",
                wizard_completed=True,
            )
        )

    tasks = container.tasks
    if not tasks.list(owner_user_id=DEMO_OWNER):
        tasks.create(title="Review morning briefing", owner_user_id=DEMO_OWNER)
        tasks.create(title="Approve the draft reply to Sam", owner_user_id=DEMO_OWNER)
        tasks.create(title="Try asking AURA in Chat", owner_user_id=DEMO_OWNER)

    memories = container.memories
    if not memories.list(DEMO_OWNER, limit=5):
        memories.create(
            DEMO_OWNER,
            kind="preference",
            content="Prefers morning meetings before 11:00.",
            actor=DEMO_OWNER,
        )
        memories.create(
            DEMO_OWNER,
            kind="person",
            content="Sam is a collaborator who prefers email over chat.",
            actor=DEMO_OWNER,
        )

    audit.record(
        DEMO_MARKER,
        DEMO_OWNER,
        {"message": "Demo workspace ready", "simulated": True},
    )
    audit.record(
        "demo.banner",
        DEMO_OWNER,
        {"message": "This is a simulated workspace. External actions are labeled SIMULATED."},
    )
    return {"seeded": True, "owner": DEMO_OWNER}
