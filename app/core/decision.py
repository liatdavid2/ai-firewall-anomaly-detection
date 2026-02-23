def decide(policy, anomaly_score):

    # Policy short-circuit
    if policy is not None and policy.action in ["allow", "block"]:
        return policy.action

    # No score available => conservative
    if anomaly_score is None:
        return "alert"

    if anomaly_score > 0.8:
        return "block"
    if anomaly_score > 0.5:
        return "alert"
    return "allow"
