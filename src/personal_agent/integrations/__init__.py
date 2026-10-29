"""External service adapters, added feature by feature.

Each integration owns its API client, its authentication, its data mapping, and its
service-specific error handling — all inside its own package. The core and services
learn about an integration only through a local Protocol defined in that package and
the tools wrapping it, so nothing above needs to change when one is added or removed.

Planned (not stubbed here): google (gmail, calendar, drive, docs, sheets),
telegram, linkedin, facebook.
"""
