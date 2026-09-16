"""
Merge Sorted Payment Streams

You receive payment records from two systems. Each list is already sorted by
created_at ascending.

Implement merge_payments(a, b).

Each payment is a dictionary with:

* "payment_id": string
* "created_at": integer timestamp
* "amount": number

Rules:

* Return one sorted list containing all payments.
* Keep stable ordering when timestamps are equal: records from a should come
  before records from b for the same timestamp.
* Do not use sorted() on the combined list.
* Time complexity should be O(len(a) + len(b)).

Senior follow-up:

How would you merge 100 sorted streams?
"""

from typing import Dict, List


def merge_payments(a: List[Dict], b: List[Dict]) -> List[Dict]:
    # Your code goes here
    pass


if __name__ == "__main__":
    a = [
        {"payment_id": "a1", "created_at": 1, "amount": 10},
        {"payment_id": "a2", "created_at": 4, "amount": 20},
        {"payment_id": "a3", "created_at": 4, "amount": 30},
    ]
    b = [
        {"payment_id": "b1", "created_at": 2, "amount": 10},
        {"payment_id": "b2", "created_at": 4, "amount": 40},
        {"payment_id": "b3", "created_at": 7, "amount": 50},
    ]

    result = merge_payments(a, b)
    assert [payment["payment_id"] for payment in result] == [
        "a1",
        "b1",
        "a2",
        "a3",
        "b2",
        "b3",
    ]
    assert merge_payments([], b) == b
    assert merge_payments(a, []) == a

    print("All tests passed!")
