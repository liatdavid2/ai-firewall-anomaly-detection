from fastapi import APIRouter, HTTPException
from app.models.policy import Policy, PolicyUpdate
from app.services.policy_engine import save_policy, update_policy

router = APIRouter()

@router.post("/policies", status_code=201)
def create_policy(policy: Policy):
    ok = save_policy(policy)
    if not ok:
        raise HTTPException(status_code=409, detail="policy_id already exists")
    return {"message": "policy created"}

@router.put("/policies/{policy_id}")
def modify_policy(policy_id: str, update: PolicyUpdate):
    updated = update_policy(policy_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="policy not found")
    return {"message": "policy updated"}
