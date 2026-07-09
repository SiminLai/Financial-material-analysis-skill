def route_after_risk(state):

    risk = state.get("risk")

    if risk is None:
        raise ValueError(
            "state is missing required key: 'risk'"
        )

    risk_score = risk.get("risk_score")

    if risk_score is None:
        raise ValueError(
            "risk is missing required key: 'risk_score'"
        )


    # High-risk cases require external evidence
    if risk_score >= 0.1:
        return "browser"


    return "report"