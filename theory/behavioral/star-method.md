# The STAR method for behavioral questions

A **behavioral question** is any question that starts with "tell me about a time...". The interviewer isn't testing what you know. They're using how you acted in the past to predict how you'll act in their team. **STAR** (Situation, Task, Action, Result) is a four-part structure that keeps your answer short, concrete and about *you*.

The stories themselves have to come from your own experience. This doc gives you the structure, a worked example, and a way to prepare. For more practice questions with model answers, see [ownership-troubleshooting-questions.md](../questions/ownership-troubleshooting-questions.md).

## TL;DR

- **STAR = Situation, Task, Action, Result.** One sentence of context, what was your responsibility, what *you* did, and what changed, with a number.
- **Most of the time goes on the Action.** Aim for about 90 seconds in total, with roughly 60% of it on what you did and why.
- **Say "I", not "we".** The interviewer is hiring you, not your old team.
- **End with a number and a lesson.** "Latency dropped from 40 min to 6 min, and I now add a row-count check to every new load" beats "it went well".
- **Prepare 4–6 stories, not 40 answers.** One good story can answer several different questions if you change which part you emphasize.

---

## The problem

Without a structure, a behavioral answer usually goes wrong in one of three ways:

1. **Too much setup.** You spend two minutes explaining the company, the stack and the org chart, and the interviewer's attention is gone before anything happens.
2. **No "you" in it.** "We migrated to Snowflake, we fixed the pipeline, we shipped it." The interviewer still doesn't know what *you* did.
3. **No ending.** The story just stops. There's no result, so it's unclear whether anything actually got better.

The interviewer is usually filling in a scorecard with signals like ownership, judgment, communication and handling conflict. An answer that rambles makes those signals hard to find, even if the underlying story is strong.

---

## How STAR works

| Part | What it answers | Length | What to include |
|---|---|---|---|
| **S**ituation | Where and when? | 1–2 sentences | Just enough context to follow the story, including the scale if it matters ("50 dbt models, 3 analysts depending on them") |
| **T**ask | What was *your* job here? | 1 sentence | Your responsibility or the goal, and why it was hard or mattered |
| **A**ction | What did *you* do? | 3–5 sentences, about 60% of the answer | The specific steps you took, the options you considered, and *why* you chose what you chose |
| **R**esult | What changed? | 1–2 sentences | A number (time, cost, error rate, users), plus what you learned or would do differently |

The Action is where you earn the points, because that's where your judgment shows. Put your reasoning in it: "I considered X, but chose Y because...". A list of steps with no reasons sounds like you followed instructions, and a decision with a reason sounds like you made one.

The Result needs a number whenever possible. If you don't have an exact figure, give an honest approximation ("roughly halved the run time") rather than none. The lesson at the end shows that you reflect on your work, which interviewers weigh heavily for senior roles.

---

## A worked example

**Question:** "Tell me about a production issue you owned."

**Weak answer:**

> "We had a problem with our pipeline once where some data was missing. We looked into it and it turned out to be a config issue, so we fixed it and added some monitoring. It was fine after that."

It's all "we", there's no scale, the Action doesn't say what was done or why, and the Result has no number.

**Strong answer, using STAR:**

> **Situation:** "I owned the nightly Snowflake load that fed our finance dashboards, about 2 million rows a night."
>
> **Task:** "One morning the row-count check flagged that the load was 8% below its 7-day average, even though the job had succeeded. It was on me to find out why before finance used the numbers."
>
> **Action:** "I checked `COPY_HISTORY` and saw the load was running with `ON_ERROR = CONTINUE`, so malformed rows were being skipped silently. Instead of re-running the whole load, I moved the rejected rows into a quarantine table so I could see what was wrong with them. They came from a new date format in one source file, so I fixed the parsing and reprocessed only that day. Then I added an alert on the rejected-row count, because the real problem was that a load could succeed while throwing data away."
>
> **Result:** "Finance had correct numbers by 10 a.m. and the gap was closed. We've had two similar format changes since, and the alert caught both within minutes. What I took from it is that a load that succeeds while dropping rows is worse than one that fails."

That takes about 75 seconds to say. Most of it is the Action, it says "I" throughout, and it ends with a number and a lesson.

---

## My stories

### Halving a Databricks workflow's run time (12 h → 6 h)

**What I have so far:** "After some days evaluating Databricks runs of one specific workflow, I updated the query and instead of 12 hours it now takes only 6 hours."

That sentence covers the Action and the Result, but not yet the Situation or the Task. Below it's split into STAR, with the gaps marked `[fill in]`.

| Part | What I have | What to add |
|---|---|---|
| **Situation** | A Databricks workflow that took 12 hours | `[fill in]` What the workflow produced and who depended on it. Why 12 hours was a problem: it missed a morning deadline, it cost too much compute (DBUs), or a failure couldn't be re-run the same day |
| **Task** | *(missing)* | `[fill in]` Was this assigned to me, or did I notice it and take it on myself? Taking it on unasked is a stronger ownership signal |
| **Action** | Spent several days analyzing the workflow's runs, then rewrote the query | `[fill in]` *How* I found the problem (Spark UI, `explain()`, run-time history per task), *what* the problem was (a shuffle, skew, a full scan with no pruning, a bad join, reprocessing all history), *what* I changed, and any option I considered and rejected |
| **Result** | 12 h → 6 h, a 50% reduction | `[fill in]` What that unlocked (data ready before the business day, a same-day re-run is now possible) and the approximate cost saved per run or per month. Then the lesson |

**Draft answer** (replace the brackets before practicing it out loud):

> **Situation:** "We had a Databricks workflow that built `[what it produced]` for `[who used it]`, and it took 12 hours to run. That meant `[the consequence: data arrived late / it cost X per run / a failure couldn't be re-run the same day]`."
>
> **Task:** "`[I was asked to / I decided to]` find out why it was so slow and bring the run time down."
>
> **Action:** "Rather than guessing, I spent a few days going through the workflow's runs to find where the time actually went. `[Using the Spark UI / the task durations]`, I found that `[the root cause]`. I rewrote the query to `[the change]`. `[Optionally: I considered scaling up the cluster instead, but that would have raised the cost without fixing the cause.]`"
>
> **Result:** "The run time dropped from 12 hours to 6, half of what it was. That meant `[the business effect]` and saved roughly `[cost]`. The lesson I took is `[e.g. measure before optimizing: the slow part wasn't where I first assumed]`."

**Follow-up questions to be ready for:** "What exactly was slow?", "How did you confirm the output was still correct after the rewrite?" (for example, comparing row counts and totals between the old and new versions), and "Why not just use a bigger cluster?"

**Questions this story can answer:** a time you improved a system, a performance problem you solved, ownership, a technical decision.

---

## Preparing: build a story bank

You don't need a separate story for every possible question. Prepare **4–6 strong stories** and learn to point each one at different questions. Cover at least these:

| Story type | Questions it can answer |
|---|---|
| **A production incident** | "A time something broke", "a time you worked under pressure", "a mistake you made" |
| **A technical decision or refactor** | "A hard trade-off", "a time you improved a system", "a time you simplified something" |
| **A disagreement** | "A conflict with a colleague", "a time you pushed back", "a time you changed your mind" |
| **Something you delivered alone** | "Ownership", "working with ambiguity", "a project you're proud of" |
| **A failure** | "Your biggest mistake", "a project that didn't go to plan", "feedback you received" |
| **Helping someone else** | "Mentoring", "leadership without authority", "improving how the team works" |

For each story, write down in a few bullet points (not a script):

- the one-sentence Situation and Task,
- the 2–3 key decisions in the Action, with the reason for each,
- the number in the Result,
- the lesson.

Then **say each story out loud**, with a timer, until it fits in 90 seconds without reading. Reading your notes doesn't prepare you. Saying the story does.

---

## Decide: which story, and what to emphasize

- **Match the story to the signal behind the question.** "A conflict" is really testing whether you disagree respectfully and commit to a decision. "A mistake" is testing whether you own it and prevent a repeat. Pick the story that shows that signal best, not the most impressive one.
- **Reuse a story by shifting the emphasis.** The incident above answers "a time you worked under pressure" if you stress the deadline, and "a mistake" if it was your config that caused it.
- **Prefer recent and relevant stories.** For a senior data role, one story about a pipeline you owned end to end beats three about university projects.
- **Keep one backup story per type**, because you'll sometimes be asked "can you give me another example?"

---

## Failure modes

- **The "we" answer.** It's the most common failure. Talk about the team where it's true, but make your own part explicit: "the team decided to migrate, and I owned the backfill".
- **The endless Situation.** If you're still giving context after 20 seconds, cut it. The interviewer will ask if they need more.
- **The hero story.** A story where you were right and everyone else was wrong comes across as poor collaboration. Show that you listened, and that you'd have committed to the other option if the evidence had pointed that way.
- **The fake failure.** "My weakness is that I work too hard" signals that you can't reflect honestly. Pick a real, moderate mistake and spend most of the time on what you changed afterwards.
- **No follow-up depth.** Interviewers often dig in: "why that approach?", "what would you do differently?", "what did your manager think?" If the story isn't really yours, it falls apart here. Only tell stories you can answer three follow-ups about.

---

## Self-check

<details><summary><b>Q1.</b> What do the four letters of STAR stand for, and roughly how should you split a 90-second answer between them?</summary>

Situation, Task, Action, Result. Spend about 10% on the Situation, 10% on the Task, 60% on the Action and 20% on the Result. The Action is where your judgment shows, so it gets most of the time.

</details>

<details><summary><b>Q2.</b> Your answer says "we" in almost every sentence. Why is that a problem, and how do you fix it without taking credit you don't deserve?</summary>

The interviewer is assessing you, not your old team, and "we" hides what you personally did. Keep "we" for the team's decisions and outcomes, and use "I" for your own part: "the team chose to migrate, and I designed and ran the backfill". That's accurate and still shows your contribution.

</details>

<details><summary><b>Q3.</b> What should a strong Result contain?</summary>

A concrete outcome, ideally a number (run time, cost, error rate, hours saved, users affected), plus what you learned or would do differently. If you don't have an exact figure, an honest approximation is better than nothing.

</details>

<details><summary><b>Q4.</b> You're asked "tell me about a mistake you made". Which story type do you pick, and what does the interviewer really want to see?</summary>

A real failure or incident that you caused or contributed to, not a disguised strength. They want to see that you own it without excuses, that you fixed the immediate problem, and above all that you changed something so it wouldn't happen again. Spend most of the answer on the fix and the prevention.

</details>

<details><summary><b>Q5.</b> Why prepare 4–6 stories instead of an answer for every common question?</summary>

There are far more possible questions than you can script, and memorized scripts sound rehearsed. A few well-practiced stories can each answer several questions by changing the emphasis, and because they're real and familiar, they hold up under follow-up questions.

</details>

---

## Related

- [ownership-troubleshooting-questions.md](../questions/ownership-troubleshooting-questions.md): behavioral and production-judgment questions with model answers
- [llm-prompting-and-evals.md](../ai/llm-prompting-and-evals.md): talking through your work in a live coding round
