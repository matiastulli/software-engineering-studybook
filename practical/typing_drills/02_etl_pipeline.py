# ============================================================
# DRILL: Mini ETL — pull -> transform -> load
# ============================================================
# Same rules as drill 01: AI/autocomplete off, say the plan out loud
# before you type it, don't peek ahead. Target: ~20-25 min.
#
# Scenario: you're handed a messy export of client invoice records
# (think: a client's CRM export). Pull it, decide out loud what to do
# about the messy/ambiguous bits, then load the cleaned result.

# --- Given: the raw "source" data (already provided, don't retype) ---
RAW_RECORDS = [
    {"client_id": "C001", "name": "  Acme Corp ", "amount": "1200.50", "invoiced_at": "2026-01-15"},
    {"client_id": "C002", "name": "Globex Inc", "amount": "980", "invoiced_at": "01/20/2026"},
    {"client_id": "C001", "name": "Acme Corp", "amount": "1200.50", "invoiced_at": "2026-01-16"},  # duplicate-ish
    {"client_id": "C003", "name": "Initech", "amount": None, "invoiced_at": "2026-02-02"},
    {"client_id": "C004", "name": "Umbrella LLC", "amount": "not_a_number", "invoiced_at": "2026-02-05"},
]


# --- STEP 1: Pull ---
# Write pull() -> list[dict] that just returns RAW_RECORDS.
# (In a real integration this would hit an API or read a CSV — the
# point is isolating "get the raw data" as its own step even when
# it's trivial, since that's the piece that changes per client.)


# (type it below)


# --- STEP 2: Inspect before you touch it ---
# Loop over the records and print anything that looks wrong or
# ambiguous: missing amount, non-numeric amount, inconsistent date
# format, a name needing a trim. Say each issue out loud as you spot
# it — surface problems before deciding what to do about them.


# (type it below)


# --- STEP 3: Transform — normalize the easy stuff ---
# Write normalize(record) -> dict returning a NEW dict with:
#   - name: whitespace-stripped
#   - client_id: unchanged
#   - invoiced_at: converted to ISO "YYYY-MM-DD" (handle both
#     "2026-01-15" and "01/20/2026" input formats)
# Leave amount untouched for now — that's Step 4.


# (type it below)


# --- STEP 4: Transform — the judgment call ---
# Write clean_amount(record) -> float | None that converts a
# numeric-looking string amount to float, and returns None (without
# crashing) for missing or non-numeric amounts.
# Decide OUT LOUD what should happen downstream to a record with
# amount=None — drop it, zero it, or flag it for someone to check?
# There's no single right answer; what's graded is making a call and
# saying why, not which call you make.


# (type it below)


# --- STEP 5: Transform — dedupe ---
# Write dedupe(records) -> list[dict] that collapses records sharing
# the same client_id + amount, keeping only the one with the latest
# invoiced_at. Decide out loud what "duplicate" means here before you
# code it — this is the same shape as a real duplicate-detection bug.


# (type it below)


# --- STEP 6: Load ---
# Write load(records) -> None that "loads" by printing each cleaned
# record in a fixed format, e.g.:
#   LOADED: C001 | Acme Corp | $1200.50 | 2026-01-16
# and separately prints a one-line summary of anything skipped and
# why, e.g.: "SKIPPED C003: no amount".


# (type it below)


# --- STEP 7: Wire the pipeline together ---
# Write run_pipeline() that calls: pull -> normalize each record ->
# clean_amount each record -> dedupe -> load, in that order. Call it
# at the bottom of the file.


# (type it below)
