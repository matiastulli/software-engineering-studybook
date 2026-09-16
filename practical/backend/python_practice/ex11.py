"""
Policy Premium Adjustments

In property and casualty insurance, a common backend task is processing
policy transactions and producing a clean result.

Implement calculate_final_premium(base_premium, adjustments).

adjustments is a list of dictionaries. Each dictionary has:

* "type": either "flat" or "percent"
* "amount": a number

Rules:

* Start with base_premium.
* Apply adjustments in the order given.
* A flat adjustment adds amount directly.
* A percent adjustment adds current_premium * amount / 100.
* Round only once at the end to 2 decimal places.
* The final premium can never be lower than 0.

Examples:

base_premium = 1000
adjustments = [
    {"type": "flat", "amount": 50},
    {"type": "percent", "amount": 10},
]

Result: 1155.0

Why: 1000 + 50 = 1050, then +10% = 1155.

Senior follow-up:

How would you handle invalid adjustment types in production?
Would you raise an exception, skip them, or record a validation error?
"""

from typing import Dict, List


def calculate_final_premium(base_premium: float, adjustments: List[Dict]) -> float:

    if adjustments == []:
        return base_premium

    total = base_premium

    for adjustment in adjustments:

        if adjustment["type"] == "flat":

            total += adjustment["amount"]

        elif adjustment["type"] == "percent":

            total += total * adjustment["amount"] / 100

    if total < 0:
        total = 0

    return round(total, 2)


if __name__ == "__main__":
    assert calculate_final_premium(1000, []) == 1000
    assert calculate_final_premium(1000, [{"type": "flat", "amount": 50}]) == 1050
    assert (
        calculate_final_premium(
            1000,
            [
                {"type": "flat", "amount": 50},
                {"type": "percent", "amount": 10},
            ],
        )
        == 1155
    )
    assert (
        calculate_final_premium(
            200,
            [
                {"type": "percent", "amount": -50},
                {"type": "flat", "amount": -200},
            ],
        )
        == 0
    )
    assert (
        calculate_final_premium(
            99.99,
            [{"type": "percent", "amount": 7.5}],
        )
        == 107.49
    )

    print("All tests passed!")
