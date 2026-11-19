"""Conservative preview, not a legally approving workflow executor."""
from .schema import WorkflowDefinition
from .validator import topological_order
from .rules import evaluate

def simulate(wf: WorkflowDefinition, facts: dict, completed: set[str]):
    order = topological_order(wf)
    node_map = {node.id: node for node in wf.nodes}
    result: dict[str, str] = {}
    for node_id in order:
        node = node_map[node_id]
        deps = [edge for edge in wf.edges if edge.target == node_id]
        if not node.enabled:
            result[node_id] = "SKIPPED_CONFIG"
            continue
        node_cond = evaluate(node.when, facts)
        if node_cond is False:
            result[node_id] = "SKIPPED_CONDITION"
            continue
        if node_cond is None:
            result[node_id] = "BLOCKED_UNKNOWN_CONDITION"
            continue
        if node_id in completed:
            result[node_id] = "COMPLETED"
            continue
        valid_inputs = [edge for edge in deps if evaluate(edge.when, facts) is True]
        missing_conditions = [edge for edge in deps if evaluate(edge.when, facts) is None]
        if missing_conditions:
            result[node_id] = "BLOCKED_UNKNOWN_CONDITION"
        elif deps and not valid_inputs:
            result[node_id] = "SKIPPED_BRANCH"
        elif all(result.get(edge.source) == "COMPLETED" for edge in valid_inputs):
            result[node_id] = "AVAILABLE"
        else:
            result[node_id] = "WAITING_DEPENDENCIES"
    return result
