"""
Policy Version Selection

Insurance systems often store multiple versions of a policy. You need to fetch
the version that was active on a specific date.

Implement find_policy_version(versions, target_date).

Each version is a dictionary with:

* "version_id": string
* "effective_date": string in YYYY-MM-DD format
* "data": dictionary

Rules:

* Return the version with the latest effective_date that is <= target_date.
* Return None if no version was active yet.
* versions may not be sorted.
* Do not mutate versions.

Example:

versions = [
    {"version_id": "v2", "effective_date": "2024-06-01", "data": {}},
    {"version_id": "v1", "effective_date": "2024-01-01", "data": {}},
]

target_date = "2024-03-15"

Result: version v1

Senior follow-up:

What database query and index would support this efficiently?
"""

from typing import Dict, List, Optional


def find_policy_version(versions: List[Dict], target_date: str) -> Optional[Dict]:
    # Your code goes here
    pass


if __name__ == "__main__":
    versions = [
        {"version_id": "v2", "effective_date": "2024-06-01", "data": {"premium": 1200}},
        {"version_id": "v1", "effective_date": "2024-01-01", "data": {"premium": 1000}},
        {"version_id": "v3", "effective_date": "2025-01-01", "data": {"premium": 1300}},
    ]

    assert find_policy_version(versions, "2023-12-31") is None
    assert find_policy_version(versions, "2024-01-01")["version_id"] == "v1"
    assert find_policy_version(versions, "2024-03-15")["version_id"] == "v1"
    assert find_policy_version(versions, "2024-06-01")["version_id"] == "v2"
    assert find_policy_version(versions, "2026-01-01")["version_id"] == "v3"

    print("All tests passed!")
