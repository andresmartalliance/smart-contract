"""Static validation of a declarative workflow, including 128+ nodes."""
from collections import deque
from .schema import WorkflowDefinition

class WorkflowInvalid(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


def topological_order(wf: WorkflowDefinition) -> list[str]:
    ids = [n.id for n in wf.nodes]
    problems: list[str] = []
    if len(set(ids)) != len(ids):
        problems.append("Duplicate node identifiers")
    node_map = {n.id: n for n in wf.nodes}
    starts = [n.id for n in wf.nodes if n.kind == "START"]
    ends = [n.id for n in wf.nodes if n.kind == "END"]
    if len(starts) != 1: problems.append("Exactly one START node is required")
    if not ends: problems.append("At least one END node is required")
    for node in wf.nodes:
        if not node.enabled and node.policy in ("LEGAL_LOCKED", "ORG_REQUIRED"):
            problems.append(f"Protected node {node.id} cannot be disabled")
        if node.kind == "APPROVAL" and node.enabled and not node.role:
            problems.append(f"Approval {node.id} has no responsible role")
    adjacency: dict[str, list[str]] = {id: [] for id in ids}
    incoming: dict[str, int] = {id: 0 for id in ids}
    for edge in wf.edges:
        if edge.source not in node_map or edge.target not in node_map:
            problems.append(f"Invalid edge {edge.source} -> {edge.target}")
            continue
        if edge.source == edge.target:
            problems.append(f"Self-dependency at {edge.source}")
        adjacency[edge.source].append(edge.target)
        incoming[edge.target] += 1
    if problems:
        raise WorkflowInvalid(problems)
    queue = deque(k for k in ids if incoming[k] == 0)
    ordered: list[str] = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for next_node in adjacency[node]:
            incoming[next_node] -= 1
            if incoming[next_node] == 0: queue.append(next_node)
    if len(ordered) != len(ids):
        raise WorkflowInvalid(["Cyclic dependencies are not supported"])
    reached = set()
    pending = deque(starts)
    while pending:
        current = pending.popleft()
        if current in reached: continue
        reached.add(current)
        pending.extend(adjacency[current])
    if reached != set(ids):
        raise WorkflowInvalid([f"Unreachable nodes from START: {sorted(set(ids)-reached)}"])
    if not any(end in reached for end in ends):
        raise WorkflowInvalid(["No reachable END"])
    return ordered
