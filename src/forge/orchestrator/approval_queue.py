
from forge.core.approvals import ApprovalStore
from forge.core.state import WorkflowState


def queue_proposed_changes(
    state: WorkflowState,
    store: ApprovalStore,
) -> dict:
    """Save successful agents' proposed changes for human approval."""

    approval_ids = []

    for result in state.get("execution_results", []):
        if result.get("status") != "completed":
            continue

        output = result.get("output")

        if not isinstance(output, dict):
            continue

        changes = output.get("proposed_changes", [])

        if not changes:
            continue

        task_id = result.get("task_id")
        agent_id = (
            result.get("assigned_agent")
            or output.get("agent_id")
        )
        summary = output.get("summary")

        if not isinstance(task_id, str) or not task_id:
            raise ValueError("Approval proposal has no task ID.")

        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("Approval proposal has no agent ID.")

        if not isinstance(summary, str) or not summary:
            raise ValueError("Approval proposal has no summary.")

        request = store.create_request(
            project_id=state["project_id"],
            task_id=task_id,
            agent_id=agent_id,
            summary=summary,
            changes=changes,
        )

        approval_ids.append(request.approval_id)

    events = []

    if approval_ids:
        events.append(
            f"Created {len(approval_ids)} pending approval request(s)."
        )
        status = "awaiting_approval"
    else:
        events.append("No file changes require approval.")
        status = state.get("status", "completed")

    return {
        "approval_ids": approval_ids,
        "status": status,
        "events": events,
    }
