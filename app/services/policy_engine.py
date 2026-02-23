from typing import Dict, Any, Optional
from app.models.policy import Policy, PolicyUpdate, Condition
from app.models.connection import ConnectionRequest
from app.services.file_store import load_json, save_json

POLICIES_FILE = "data/policies.json"

def _evaluate_condition(conn: ConnectionRequest, cond: Condition) -> bool:
    value = getattr(conn, cond.field)

    # Normalize to string for compare because policy JSON stores "value" as string
    if cond.field == "destination_port":
        left = str(int(value))
    else:
        left = str(value)

    right = cond.value

    if cond.operator == "==":
        return left == right
    if cond.operator == "!=":
        return left != right
    return False

def _policy_matches(conn: ConnectionRequest, policy: Policy) -> bool:
    return all(_evaluate_condition(conn, c) for c in policy.conditions)

def load_policies() -> Dict[str, Any]:
    return load_json(POLICIES_FILE)

def save_policy(policy: Policy) -> bool:
    data = load_policies()
    if policy.policy_id in data:
        return False
    data[policy.policy_id] = policy.model_dump()
    save_json(POLICIES_FILE, data)
    return True

def update_policy(policy_id: str, update: PolicyUpdate) -> bool:
    data = load_policies()
    if policy_id not in data:
        return False
    data[policy_id]["conditions"] = [c.model_dump() for c in update.conditions]
    data[policy_id]["action"] = update.action
    save_json(POLICIES_FILE, data)
    return True

def find_matching_policy(conn: ConnectionRequest) -> Optional[Policy]:
    data = load_policies()
    for p in data.values():
        policy = Policy(**p)
        if _policy_matches(conn, policy):
            return policy
    return None
