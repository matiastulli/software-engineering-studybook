"""
SQL Reasoning: Policies and Claims

This is a written exercise. You do not need to run this file.

Tables:

policies
--------
id INTEGER PRIMARY KEY
policy_number TEXT
state TEXT
active BOOLEAN

claims
------
id INTEGER PRIMARY KEY
policy_id INTEGER
status TEXT
amount DECIMAL
created_at TIMESTAMP

Task 1:

Write a SQL query that returns active policies with at least one open claim.
Return:

* policy_number
* state
* open_claim_count
* open_claim_total_amount

Task 2:

Write a SQL query that returns the top 5 states by total closed claim amount.

Task 3:

Explain the indexes you would add if these queries were slow.

Senior follow-up:

How would your answer change if claims has 100 million rows?
Think about indexes, partitioning, caching, and read replicas.
"""


TASK_1_QUERY = """
-- Write your SQL here.
"""


TASK_2_QUERY = """
-- Write your SQL here.
"""


INDEX_NOTES = """
Write your index notes here.
"""
