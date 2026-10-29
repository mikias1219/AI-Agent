"""Persistence infrastructure: SQLAlchemy models, sessions, repositories, migrations.

Only this layer knows the database exists. Everything above consumes the
`core.ports` repositories.
"""
