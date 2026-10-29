"""Application services: the only layer interfaces call.

Each service owns a use case end-to-end (load context → run agent → persist),
which keeps frontends free of orchestration logic.
"""
