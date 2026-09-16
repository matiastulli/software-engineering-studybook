# Ownership, Production & Communication — Questions

The JD bullet most people have no story for: *end-to-end ownership, troubleshooting in production, shipping independently*. These are behavioural, so the content is **your** experience. What follows is the structure that makes it land, plus English phrasing.

---

## Structure

<details><summary><b>Q1.</b> What's the format for a behavioural answer?</summary>

**A.** **STAR**, with numbers, in about 90 seconds:

- **Situation:** one sentence of context.
- **Task:** what was actually your responsibility.
- **Action:** what *you* did, specifically. Say "I", not "we".
- **Result:** quantified, plus what you'd do differently.

The two failure modes are drifting into team credit ("we decided...") and having no number at the end. Prepare four stories and reuse them: an incident, a refactor, a disagreement, and a delivery you owned alone.
</details>

<details><summary><b>Q2.</b> "Tell me about a production incident you owned."</summary>

**A.** Structure it as **detection → diagnosis → mitigation → fix → prevention**. Interviewers care most about the last step.

*"An overnight load silently dropped 8% of rows. I found it because the row-count check flagged a deviation from the 7-day average; the load itself succeeded, so nothing else caught it. `ON_ERROR = CONTINUE` was discarding malformed rows without alerting. I quarantined the rejected rows, reprocessed the day, then added an alert on the rejected-row count in `COPY_HISTORY`. The lesson I took is that a load that succeeds while discarding rows is worse than one that fails."*

The prevention step is what separates "I fixed it" from "I own this system".
</details>

<details><summary><b>Q3.</b> "Describe a time you disagreed with a technical decision."</summary>

**A.** Show that you argued with evidence and then committed either way.

*"The team wanted Kafka for a pipeline doing about 300 events a second. I pulled the numbers: one Kinesis shard covered it, and we had nobody on call who'd run brokers. I wrote up both options with the cost and the operational burden, and we went with Kinesis. If the volume had justified Kafka I'd have supported it, but nobody had done the arithmetic."*

Disagreement plus data plus commitment. Never tell a story where you were simply right and everyone else was wrong.
</details>

<details><summary><b>Q4.</b> "Tell me about something you delivered independently."</summary>

**A.** Emphasise the decisions you made without being told, and the points where you chose to check in.

The signal they want: handed an ambiguous problem, you come back with something working, having asked the two questions that actually mattered rather than twenty or zero. Close with a number, such as time to first version, users, or the cost or hours it saved.
</details>

---

## Production judgement

<details><summary><b>Q5.</b> The nightly pipeline failed and finance needs numbers in two hours. What do you do?</summary>

**A.** Communicate first: tell finance the status and an ETA before they ask. Then triage:
1. **Blast radius:** which models are stale, which dashboards are affected.
2. **Fastest safe path** to a correct number, often re-running one branch rather than the whole DAG.
3. **Fix properly afterwards**, not during.

The mistake is going quiet for 90 minutes while you debug. Visibility during an incident matters as much as the fix. Send a short update every 30 minutes, even when it's "no change".
</details>

<details><summary><b>Q6.</b> A stakeholder says "the number looks wrong". How do you investigate?</summary>

**A.** First establish **which number, compared to what**. Usually they're comparing two definitions rather than finding a bug, and half of these end there.

If it's real:
1. Check freshness: is the data even current?
2. Compare row counts against history.
3. Walk the lineage backwards layer by layer. Layered models make this a bisect instead of a search.

Then report back in their language, not yours: what was wrong, what it affected, what's fixed, and what prevents it recurring.
</details>

<details><summary><b>Q7.</b> How do you decide whether to fix forward or roll back?</summary>

**A.** Under uncertainty, roll back: it's quick and reversible, and understanding can happen calmly afterwards.

- **Roll back** when the blast radius is growing or the cause isn't understood. A clone swap or a revert takes seconds.
- **Fix forward** when the cause is understood, the fix is small, and rolling back would itself cause damage (a partially migrated consumer, say).

The costs are asymmetric: an unnecessary rollback costs minutes; a wrong fix forward under pressure can cost the day.
</details>

<details><summary><b>Q8.</b> You're asked to ship something you think is a bad idea. What do you do?</summary>

**A.** State the concern once, concretely, with the consequence and its cost. If the decision stands, build it properly and instrument it, so the consequence is visible when it arrives.

Building it badly on purpose, or relitigating it weekly, both read as junior. Disagree, commit, and make the failure mode observable.
</details>

<details><summary><b>Q13.</b> First call with a customer: they want "a dashboard of all our loads, real-time". How do you scope it?</summary>

**A.** Turn the solution they asked for back into the decision they need to make, then agree the smallest version that proves value. As a Forward Deployed Engineer, scoping is half the job.

Ask the few questions that change the design:
- **Who acts on it, and what do they do differently?** That reveals the actual metric.
- **How fresh, really?** "Real-time" often means "updated before the 8am standup". Seconds vs 15 minutes is a 10× difference in cost and complexity.
- **Where does the data live, and who owns access?** Usually the actual blocker.
- **What's "done" in two weeks?**

Then restate it in writing: *"v1 is loads by status and carrier, refreshed every 15 minutes, from your TMS replica, for the ops team. Real-time alerts are a v2 if v1 gets used."* Committing to a small version beats agreeing to everything.
</details>

---

## English phrasing

<details><summary><b>Q9.</b> How do you buy thinking time in English without sounding lost?</summary>

**A.** Structure the pause instead of filling it:

- *"Let me make sure I understand the constraint before I answer."*
- *"There are two ways to approach this. Let me take the simpler one first."*
- *"Give me a second to think about the failure modes."*

Silence while thinking reads as competent; "um, so, basically" for fifteen seconds doesn't. Practising three of these until they're automatic is worth more than vocabulary.
</details>

<details><summary><b>Q10.</b> Useful phrases for hedging precisely.</summary>

**A.** Being precise about your own certainty is a seniority signal:

- *"I'd have to check, but my understanding is…"*
- *"That depends on whether X. If X, then A; otherwise B."*
- *"I haven't used that in production, but the model I'd apply is…"*
- *"I don't know. Here's how I'd find out."*

That last one is a strong answer, not a weak one, as long as the method that follows is real.
</details>

<details><summary><b>Q11.</b> How do you ask for clarification without losing momentum?</summary>

**A.** Ask, propose and continue in one move: *"Is this internal-facing or customer-facing? I'll assume customer-facing, which means I care more about p99 latency. Tell me if that's wrong."*

Never stop and wait. Stating the assumption and proceeding is what a colleague does; blocking on the answer is what a junior does.
</details>

<details><summary><b>Q12.</b> How do you close a system design interview well?</summary>

**A.** Summarise unprompted in about 60 seconds: the design, the one number that drove it, the main trade-off you accepted, and the growth path.

*"So: Kinesis with truck_id as the partition key, Lambda to DynamoDB and S3, scheduled silence detection. It's sized for 333 events a second. The trade-off is up to a minute of alert latency in exchange for much simpler operations. If the fleet grows past a few hundred thousand trucks, I'd move detection into a stream processor with per-truck timers."*

Most candidates run out of time mid-sentence. A deliberate summary is memorable and costs a minute.
</details>
