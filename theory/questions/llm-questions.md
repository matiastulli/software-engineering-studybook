# LLM Agents, Prompts & Evals — Questions

From [../ai/llm-prompting-and-evals.md](../ai/llm-prompting-and-evals.md). Asked in full-stack + LLM FDE loops (voice agents, check calls, carrier sales). The domain here is trucks and loads, as in the rest of the bank.

---

## Building agents

<details><summary><b>Q1.</b> "How would you build an agent for X?" Walk me through it.</summary>

**A.** An agent is an LLM in a loop with a narrow objective, a few real tools, and guardrails enforced in code, and you only know it works once you've scored it on transcripts. Walk the pieces in order:

1. **Scope:** a narrow job ("run a check call and log the status"), not "be helpful".
2. **Tools:** functions with a name, typed arguments and a description (`get_load(load_number)`, `update_status(load_number, status)`). The model *requests* a call; your code executes it.
3. **System prompt:** identity, objective order, when to use each tool, guardrails, escalation, tone.
4. **Loop:** user turn → model responds or calls a tool → code runs it → result goes back → repeat until done or escalated.
5. **State:** conversation history plus injected context (the load record, the caller).
6. **Guardrails twice:** in the prompt (soft) and in code (hard validation).
7. **Evals:** a fixed set of transcripts scored on a rubric.
8. **Monitor and iterate:** log every call, score it, and feed failure patterns back.
</details>

<details><summary><b>Q2.</b> How do you structure a production system prompt?</summary>

**A.** Treat it as requirements, in sections, each defending against a named failure mode.

| Section | Defends against |
| --- | --- |
| Identity / role | Generic persona; denying it's an AI when asked |
| Objective, in order | Rambling, asking things out of sequence |
| Tools + when to call them | Describing an action instead of taking it; invented facts |
| Guardrails ("never X") | Scope creep: quoting a rate or promising a refund it can't authorise |
| Escalation triggers | Handling what a human must handle |
| Tone / channel | Chat-length sentences on a phone call |

In the interview, justify each guardrail by the call that went wrong. Reciting the guardrail alone isn't enough.
</details>

<details><summary><b>Q3.</b> What goes in the system prompt vs the per-call context?</summary>

**A.** The system prompt holds fixed instructions, the same for every call of the workflow. Per-call data (the load record, the caller's name, history so far) goes into injected context or variables.

Mixing them means rewriting and retesting the prompt for every case instead of parameterising it. It also makes caching and evals harder, because the "prompt version" changes on every call. Bridge: it's a parameterised query vs string-concatenated SQL.
</details>

---

## Guardrails & failures

<details><summary><b>Q4.</b> Why enforce guardrails in code if the prompt already says "never"?</summary>

**A.** Because a prompt is a strong suggestion, not a guarantee. A model will occasionally emit a status outside the enum or a rate it shouldn't quote. The prompt lowers the frequency; code makes the invalid action impossible.

Concretely:
- Constrain outputs (enum / JSON schema / structured outputs).
- Validate server-side, rejecting with a `422` and a message the agent can recover from.
- Check permissions in the tool: the booking tool checks the rate is within the allowed band, whatever the model says.
- Make mutating tools idempotent, because agents retry.
</details>

<details><summary><b>Q5.</b> The agent hallucinated a delivery ETA on a call. What do you do?</summary>

**A.** Diagnose which of three failures it was before adding a guardrail, because each has a different fix.

1. **No grounding available:** the agent had no tool for the ETA → add a lookup tool and make it the only allowed source.
2. **Tool available but ignored:** a prompt problem → an explicit instruction ("never state an ETA not returned by `get_load`") plus a few-shot example of the ambiguous case.
3. **Tool returned bad data:** an integration problem → fix the source; the prompt was fine.

On voice, add a fourth: **the transcript was already wrong** (ASR misheard "Laredo"). That's a transcription problem, not an LLM problem, and separating the two is a real signal of production experience.
</details>

---

## Evals

<details><summary><b>Q6.</b> How do you know a prompt change made things better, not just different?</summary>

**A.** Re-run a **fixed eval set** before and after, and compare case by case, not by eyeballing one conversation. The risk is **regression**: a fix for one edge case quietly breaks cases that used to pass.

- **Golden set:** 50–200 real or synthetic transcripts covering known edge cases, versioned alongside the prompt.
- **Rubric per case:** tool correctness, guardrail adherence, escalation, business outcome. Report pass rate *per criterion*, not one blended score.
- **Gate:** block the change if any previously passing case now fails, unless you accept it explicitly.
- **Non-determinism:** run each case a few times, and treat a small pass-rate difference as noise.

Pick an LLM-as-judge for subjective criteria; pick rule checks for anything verifiable (was `update_status` called with a valid enum?). Trade-off: a judge scales, but it must be calibrated against human labels.
</details>

<details><summary><b>Q7.</b> How would you evaluate agent quality at scale, across thousands of calls a day?</summary>

**A.** Use a **hybrid auditor**: rule-based checks for facts, an LLM judge for subjective criteria, and humans sampling for calibration. Not "a human listens to every call".

- **Rules:** tool called? arguments valid? status actually written to the TMS? call ended within budget?
- **LLM judge:** tone, whether it answered the question, whether it escalated when it should have.
- **Human sample:** a small labelled set to measure judge agreement (precision/recall), re-checked when the judge prompt or model changes.

Weight **escalation recall** highest: a missed hand-off (the agent should have escalated and didn't) costs more than an unnecessary one. Then cluster failures by root cause. One bad call is noise; ten sharing a cause is a prompt or tool gap worth fixing.
</details>

---

## Voice, latency & cost

<details><summary><b>Q8.</b> What's different about latency and model choice for a voice agent?</summary>

**A.** Every turn is **speech-to-text → LLM → text-to-speech**, and silence past roughly a second on a phone call feels broken. So the latency budget, not model quality alone, drives the design.

- **Stream everything:** partial transcripts in, streamed tokens out, start speaking the first sentence early.
- **Fewer turns beat faster turns:** a tight prompt and a narrow objective often save more end-to-end time than a faster model.
- **Model size is a business trade-off:** bigger models handle ambiguity better but add latency and cost per turn. Pick by the cost of a wrong answer (quoting a rate) vs the cost of a slow one (a routine check call).
- **Domain vocabulary:** load numbers, city pairs and carrier names are often the real bottleneck, and the fix is ASR configuration (custom vocabulary), not the prompt.
</details>
