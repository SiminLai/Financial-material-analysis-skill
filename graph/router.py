
def route_after_risk(state):
    """
    Route after risk analysis.

    Returns:
        "browser" : high-risk documents require external web search.
        "report"  : otherwise generate report directly.
    """

    risk = state.get("risk")

    if risk is None:
        raise ValueError("state is missing required key: 'risk'")

    risk_score = risk.get("risk_score")

    if risk_score is None:
        raise ValueError("risk is missing required key: 'risk_score'")

    # configurable threshold
    if risk_score >= 0.1:
        return "browser"

    return "report"