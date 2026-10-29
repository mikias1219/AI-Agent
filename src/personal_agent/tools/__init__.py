"""The controlled tool system: specs, registry, and builtins.

Every external action the model can trigger must be a registered tool; the registry
is the only execution gate. Add new tool modules under a subpackage and register
them from `bootstrap.py`.
"""
