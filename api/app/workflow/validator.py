"""Validate a versioned DAG declaratively. Structural validation is not legal approval.

This module does not depend on a fixed payment modality or institutional flow.
"""
from collections import deque
from .schema import WorkflowDefinition


class WorkflowInvalid(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("; ".join(problems))


def topological_order(wf: WorkflowDefinition) -> list[str]:
    ids = [node.id for node in wf.nodes]
    node_map = {node.id: node for node in wf.nodes}
    problems: list[str] = []
    if len(node_map) != len(ids):
        problems.append("Duplicate node identifiers")

    starts = [node.id for node in wf.nodes if node.kind == "START"]
    ends = [node.id for node in wf.nodes if node.kind == "END"]
    if len(starts) != 1:
        problems.append("Exactly one START node is required")
    if not ends:
        problems.append("At least one END node is required")

    for node in wf.nodes:
        if not node.enabled and (node.policy in ("LEGAL_LOCKED", "ORG_REQUIRED") or node.kind in ("START", "END")):
            problems.append(f"Protected node {node.id} cannot be disabled")
        if node.enabled and node.kind == "APPROVAL" and not node.role:
            problems.append(f"Approval {node.id} has no responsible role")
        if node.enabled and node.policy == "CONDITIONAL" and node.when is None:
            problems.append(f"Conditional node {node.id} has no activation condition")

        fields = node.config.get("fields", [])
        if not isinstance(fields, list):
            problems.append(f"Node {node.id} has invalid fields configuration")
        else:
            field_ids = []
            for field in fields:
                if not isinstance(field, dict) or not isinstance(field.get("key"), str) or not isinstance(field.get("label"), str):
                    problems.append(f"Node {node.id} contains an invalid field")
                    continue
                field_ids.append(field["key"])
                if not field["key"].strip() or not field["label"].strip():
                    problems.append(f"Node {node.id} contains an unnamed field")
            if len(field_ids) != len(set(field_ids)):
                problems.append(f"Node {node.id} contains duplicate field keys")

    adjacency = {node_id: [] for node_id in node_map}
    reverse = {node_id: [] for node_id in node_map}
    incoming = {node_id: 0 for node_id in node_map}
    seen_edges: set[tuple[str, str]] = set()
    for edge in wf.edges:
        if edge.source not in node_map or edge.target not in node_map:
            problems.append(f"Invalid edge {edge.source} -> {edge.target}")
            continue
        pair = (edge.source, edge.target)
        if pair in seen_edges:
            problems.append(f"Duplicate edge {edge.source} -> {edge.target}")
        seen_edges.add(pair)
        if edge.source == edge.target:
            problems.append(f"Self-dependency at {edge.source}")
        if node_map[edge.source].kind == "END":
            problems.append(f"END node {edge.source} cannot have outgoing edges")
        if node_map[edge.target].kind == "START":
            problems.append(f"START node {edge.target} cannot have incoming edges")
        adjacency[edge.source].append(edge.target)
        reverse[edge.target].append(edge.source)
        incoming[edge.target] += 1

    if problems:
        raise WorkflowInvalid(problems)

    ready = deque(node_id for node_id in node_map if incoming[node_id] == 0)
    ordered = []
    while ready:
        node_id = ready.popleft()
        ordered.append(node_id)
        for destination in adjacency[node_id]:
            incoming[destination] -= 1
            if incoming[destination] == 0:
                ready.append(destination)

    if len(ordered) != len(ids):
        raise WorkflowInvalid(["Cyclic dependencies are not supported"])

    def traverse(seeds: list[str], paths: dict[str, list[str]]) -> set[str]:
        visited: set[str] = set()
        pending = deque(seeds)
        while pending:
            current = pending.popleft()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(paths[current])
        return visited

    reached = traverse(starts, adjacency)
    reaches_end = traverse(ends, reverse)
    if reached != set(ids):
        problems.append(f"Unreachable nodes from START: {sorted(set(ids) - reached)}")
    if reaches_end != set(ids):
        problems.append(f"Nodes cannot reach END: {sorted(set(ids) - reaches_end)}")
    if problems:
        raise WorkflowInvalid(problems)
    return ordered
