"""Tiny, deterministic rules interpreter; never use eval/exec."""
from typing import Any
from .schema import Condition

UNRESOLVED = object()

def resolve_value(data: dict[str, Any], path: str):
    current: Any = data
    for item in path.split("."):
        if not isinstance(current, dict) or item not in current:
            return UNRESOLVED
        current = current[item]
    return current

def evaluate(condition: Condition | None, facts: dict[str, Any]) -> bool | None:
    if condition is None:
        return True
    val = resolve_value(facts, condition.field)
    if condition.op == "exists":
        return val is not UNRESOLVED and val is not None
    if val is UNRESOLVED:
        return None  # Unknown input must never silently become an approval.
    try:
        fn = {
          "eq": lambda: val == condition.value,
          "neq": lambda: val != condition.value,
          "in": lambda: val in condition.value,
          "gt": lambda: val > condition.value,
          "gte": lambda: val >= condition.value,
          "lt": lambda: val < condition.value,
          "lte": lambda: val <= condition.value,
        }
        return bool(fn[condition.op]())
    except (TypeError, ValueError, KeyError):
        return None
