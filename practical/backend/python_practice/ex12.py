"""
Deduplicate API Events

You receive events from an external API. Sometimes the API retries and sends
the same event more than once.

Implement deduplicate_events(events).

Each event is a dictionary with:

* "id": unique event identifier
* "timestamp": integer Unix timestamp
* "payload": any dictionary

Rules:

* Return a new list.
* Keep only one event for each id.
* If the same id appears multiple times, keep the event with the latest timestamp.
* Preserve the order of first appearance of each id in the returned list.
* Do not mutate the input list or event dictionaries.

Example:

events = [
    {"id": "a", "timestamp": 10, "payload": {"status": "old"}},
    {"id": "b", "timestamp": 12, "payload": {"status": "ok"}},
    {"id": "a", "timestamp": 15, "payload": {"status": "new"}},
]

Result:
[
    {"id": "a", "timestamp": 15, "payload": {"status": "new"}},
    {"id": "b", "timestamp": 12, "payload": {"status": "ok"}},
]

Senior follow-up:

What changes if events arrive as an infinite stream instead of a list?
"""

from typing import Dict, List
from copy import deepcopy


def deduplicate_events(events: List[Dict]) -> List[Dict]:
    """
    Deduplicate events by id, keeping the latest timestamp for each id.
    
    Args:
        events: List of event dictionaries with 'id', 'timestamp', and 'payload'
        
    Returns:
        New list with deduplicated events, preserving order of first appearance
    """
    output = []
    seen = {}

    for event in events:
        event_id = event["id"]
        if event_id not in seen:
            # First appearance - record the index and add to output
            seen[event_id] = len(output)
            output.append(deepcopy(event))
        else:
            # Check if this event has a later timestamp
            if event["timestamp"] > output[seen[event_id]]["timestamp"]:
                output[seen[event_id]] = deepcopy(event)
    
    return output



if __name__ == "__main__":
    data = [
        {"id": "a", "timestamp": 10, "payload": {"status": "old"}},
        {"id": "a", "timestamp": 15, "payload": {"status": "new"}},
        {"id": "b", "timestamp": 12, "payload": {"status": "ok"}},
    ]
    assert deduplicate_events(data) == [
        {"id": "a", "timestamp": 15, "payload": {"status": "new"}},
        {"id": "b", "timestamp": 12, "payload": {"status": "ok"}},
    ]

    assert deduplicate_events([]) == []

    data = [
        {"id": "x", "timestamp": 5, "payload": {}},
        {"id": "x", "timestamp": 4, "payload": {"ignored": True}},
    ]
    assert deduplicate_events(data) == [{"id": "x", "timestamp": 5, "payload": {}}]

    print("All tests passed!")
