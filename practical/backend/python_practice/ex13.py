"""
Claim Status Summary

Implement summarize_claims(claims).

Each claim is a dictionary with:

* "claim_id": string
* "policy_id": string
* "status": one of "open", "closed", "denied"
* "amount": number

Return a dictionary with:

* "total_claims": total number of claims
* "open_claims": number of open claims
* "closed_claims": number of closed claims
* "denied_claims": number of denied claims
* "total_paid": sum of amounts for closed claims only
* "largest_open_claim_id": claim_id of the open claim with the largest amount,
  or None if there are no open claims

Rules:

* claims is always a list.
* claim amounts are non-negative.
* If two open claims have the same largest amount, return the first one.

Senior follow-up:

How would you expose this through a REST API endpoint?
What response code would you return for malformed claim data?
"""

from typing import Dict, List, Optional


def summarize_claims(claims: List[Dict]) -> Dict[str, Optional[float]]:
    # Your code goes here
    pass


if __name__ == "__main__":
    claims = [
        {"claim_id": "c1", "policy_id": "p1", "status": "open", "amount": 500},
        {"claim_id": "c2", "policy_id": "p1", "status": "closed", "amount": 300},
        {"claim_id": "c3", "policy_id": "p2", "status": "denied", "amount": 1000},
        {"claim_id": "c4", "policy_id": "p3", "status": "open", "amount": 700},
    ]
    assert summarize_claims(claims) == {
        "total_claims": 4,
        "open_claims": 2,
        "closed_claims": 1,
        "denied_claims": 1,
        "total_paid": 300,
        "largest_open_claim_id": "c4",
    }

    assert summarize_claims([]) == {
        "total_claims": 0,
        "open_claims": 0,
        "closed_claims": 0,
        "denied_claims": 0,
        "total_paid": 0,
        "largest_open_claim_id": None,
    }

    print("All tests passed!")
