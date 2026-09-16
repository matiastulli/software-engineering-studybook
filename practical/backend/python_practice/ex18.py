"""
Design Exercise: Insurance Quote API

This is a senior-style design prompt. You do not need to code everything.
Write your answer in this file as comments or markdown-style text.

Prompt:

Design an API endpoint that creates an insurance quote.

Minimum requirements:

* The client sends applicant details, address, coverage options, and deductible.
* The system validates the request.
* The system calculates a premium.
* The system returns a quote id, premium, expiration date, and validation warnings.
* The same request retried with the same idempotency key should not create
  duplicate quotes.

Answer these:

1. What HTTP method and path would you use?
2. What would the request JSON look like?
3. What would the response JSON look like?
4. What validation errors would return 400?
5. What internal services or modules would you split this into?
6. Where would you store idempotency keys?
7. What would you log and monitor?
8. What tests would you write?

Senior follow-up:

Assume rating rules change frequently and business users configure them.
How would you avoid deploying code every time a rating rule changes?
"""


ANSWER = """
Write your design answer here.
"""
