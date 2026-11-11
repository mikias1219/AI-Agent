"""Agent-created tasks under dashboard owner appear in the workspace list."""

from personal_agent.application.tools.builtins.tasks import task_tools
from personal_agent.domain.models import ToolCall, ToolContext


def test_task_create_with_dashboard_owner_lists(tool_registry, session_factory, audit_log, ctx):
    from personal_agent.application.services.task_service import TaskService
    from personal_agent.infrastructure.persistence.repositories import TaskRepositoryImpl

    tasks = TaskService(TaskRepositoryImpl(session_factory), audit=audit_log)
    tool_registry.register_all(task_tools(tasks))
    dash = ToolContext(user_id="dashboard", session_id="s1", origin="dashboard")
    created = tool_registry.execute(
        ToolCall(id="1", name="task_create", arguments={"title": "Buy milk"}),
        dash,
    )
    assert created.ok
    listed = tool_registry.execute(ToolCall(id="2", name="task_list", arguments={}), dash)
    assert listed.ok
    assert "Buy milk" in (listed.output or "")
    # All tasks API-style list includes dashboard owner
    assert any(t.owner_user_id == "dashboard" and t.title == "Buy milk" for t in tasks.list())
