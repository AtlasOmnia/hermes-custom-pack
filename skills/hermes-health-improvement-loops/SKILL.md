---
name: hermes-health-improvement-loops
description: "Use when auditing Hermes health or evaluating explicit outcomes for improvement suggestions; keep read-only health separate from suggestion-only improvement and route implementation details to the public companion project."
version: 1.0.0
author: AtlasOmnia
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, health, audit, diagnostics, improvement, safety, read-only, suggestions]
    related_skills: [hermes-agent, hermes-self-evaluation, hermes-nightly-self-check-decisions]
---

# Hermes Health Improvement Loops

## Overview

This is a companion OPERATING PLAYBOOK for the public Hermes Health Improvement Loops project. It teaches an agent or operator how to use the project safely, interpret its outputs, and keep its two lanes separate. It is not the executable implementation, a second inventory, a replacement for Hermes documentation, or a code-level installation guide.

The executable implementation and the full current check inventory live in the public project:

- Project: https://github.com/AtlasOmnia/hermes-health-improvement-loops
- Check matrix: https://github.com/AtlasOmnia/hermes-health-improvement-loops/blob/main/docs/health-check-matrix.md

Read those sources when you need exact behavior, supported surfaces, output schemas, release changes, or implementation-level verification. This playbook intentionally summarizes the operating contract instead of copying the implementation. If this playbook and the public project disagree, treat the current public implementation and matrix as authoritative, subject to the safety boundary below.

The project provides two deliberately independent capabilities:

- A health lane that performs bounded, read-only checks against an operator-selected Hermes home.
- An improvement lane that evaluates an explicitly supplied outcome packet and produces a suggestion for human review.

An optional report may present already-produced results together. A report is presentation, not permission. Combining results must never combine input discovery, credentials, runtime authority, configuration control, scheduler control, or delivery authority.

This playbook is intentionally generic. It does not select a model, provider, route, host, transport, schedule, delivery target, profile, or account. It does not contain credentials, machine-specific locations, or private operating procedures.

## When to Use

Use this playbook when a user or agent asks to:

- perform a bounded Hermes health audit without changing the installation;
- understand whether a Hermes surface is healthy, degraded, unavailable, unknown, or not observed;
- evaluate explicit outcomes for recurring failure or quality patterns;
- prepare a review packet for possible Hermes improvement work;
- understand the boundary between operational diagnostics and improvement suggestions;
- inspect the public health-check matrix before deciding what evidence is available; or
- explain why an improvement suggestion must not automatically change Hermes.

Do not use this playbook as authority to:

- change Hermes configuration, skills, memory, sessions, scheduler state, credentials, providers, models, routes, or delivery settings;
- discover or crawl outcome sources that the operator did not explicitly provide;
- treat a health result as permission to repair, restart, reconfigure, or publish;
- treat a suggestion as an approved change;
- replace the current Hermes CLI help with remembered command syntax; or
- infer a healthy status from a missing, inaccessible, malformed, stale, or unsupported surface.

If a user wants implementation, mutation, scheduling, or publication, stop at the relevant boundary and obtain a separately scoped approval. Then load `hermes-agent` before changing Hermes or advising a change to Hermes. The companion project remains a read-only/audit and suggestion-only tool unless a separate integration is explicitly reviewed and authorized.

## Safety and authority boundary

### Authority levels

Apply these authority levels in order:

1. **Observation authority** — read bounded, permitted data from an explicit operator-selected home or explicit outcome packet.
2. **Evaluation authority** — classify observed evidence or evaluate a redacted packet under the current project rules.
3. **Suggestion authority** — describe a possible improvement for a person to review.
4. **Mutation authority** — change Hermes, its configuration, its scheduler, or any external system. This is not granted by this skill.

The default operating mode stops at suggestion authority. A health check never grants mutation authority. A repeated outcome never grants mutation authority. A report never grants mutation authority. A person must make the separate decision, define the exact target and allowlist, and authorize the mutation through the appropriate Hermes operating procedure.

### Read-only means read-only

Health work may inspect only bounded, supported surfaces through the public implementation. It must not write to the selected Hermes home, update a file in place, alter a database, prune history, rotate credentials, restart a service, create a scheduler entry, or repair a detected condition. If a tool or wrapper unexpectedly attempts a write, treat that as a failure and stop rather than approving a broader action.

Improvement work must consume only an outcome packet or fixture explicitly supplied for that evaluation. It must not search a Hermes home, crawl transcripts, infer private sources, harvest memory, or silently broaden its input set. The packet should be reviewed for sensitivity before use. Redaction reduces exposure; it does not prove that every personal or secret-like value has been removed.

External runtime state may hold package-owned ledgers, reports, or other outputs when the public implementation supports them. Keep that runtime state outside source artifacts and outside the Hermes home. Do not treat an output directory as permission to write elsewhere.

### Human-only review

Suggestions are advisory. A human must review the evidence, the classification, the proposed direction, the affected boundary, and the expected risk before any experiment or change. The human review must explicitly decide whether to reject, defer, investigate, or authorize a separately scoped mutation. A suggestion is not a patch, approval, schedule, deployment, release, or rollback.

A human must also decide whether any produced report is appropriate to share. Reports can contain operational facts even when redaction is enabled. Never publish a raw report merely because the tool completed successfully.

### Load the Hermes operating guidance first

Before changing Hermes, its installed skills, configuration, scheduler, or runtime, load `hermes-agent` and consult current Hermes documentation. Verify the live command surface rather than relying on this playbook or remembered syntax. This requirement applies even when a suggestion appears obvious or low risk.

If a separately approved task involves rendering or proposing cron commands, first inspect the current CLI help for the installed Hermes version and the relevant cron subcommand. Use only syntax confirmed by that help. This playbook does not freeze scheduler flags or provide a cron recipe.

## Operating flow

Use the following default safe flow. Keep the health and improvement lanes as two transactions with separate inputs, permissions, evidence, and failure handling.

### 1. Establish the operating boundary

Confirm that the request is an audit, evaluation, or report—not an instruction to repair Hermes. Identify the operator-selected Hermes home for health work, the explicit outcome packet for improvement work, and the external runtime location for package-owned outputs if one is needed.

Do not substitute an implicit default home when the task requires a clear audit target. Do not substitute a guessed packet, session search, transcript crawl, or live source for an explicit outcome packet. If the target or packet is absent, report the missing input and stop that lane.

Record the intended lane before execution:

- `health`: selected home, bounded read-only probe, external result destination if applicable;
- `improvement`: explicit packet, redaction/evaluation, external result destination if applicable;
- `report`: already-produced health and improvement results, with no new authority.

### 2. Inspect the current public contract

Open the public health-check matrix before interpreting a result that depends on a particular check. The matrix is the executable contract’s inventory of supported categories, inputs, limits, and expected statuses. It is more authoritative than a copied list in a prompt or an old report.

Also inspect the current Hermes CLI help whenever a task touches command syntax. Help output is version-sensitive. Do not render a scheduler command, installation command, or other operational command from memory when current help can answer it.

### 3. Render before applying anything

If the public implementation offers a manifest or setup renderer, use its dry-run or render-only mode first. The safe default is to produce a reviewable manifest or command proposal without changing Hermes files or creating scheduler state.

A rendered manifest is an artifact for inspection. It is not evidence that a job was installed, that a service is running, or that any external action succeeded. Verify the rendered inputs and boundaries before considering any separately approved next step. If a renderer requires model, provider, delivery, schedule, route, host, or similar values, those must remain explicit operator inputs; the companion playbook does not choose them.

### 4. Run the health lane

Run the bounded health audit only against the explicit Hermes home. Keep the probe scope narrow and read-only. Useful categories generally include:

- presence and readability of expected metadata;
- bounded JSON or structured-state parsing;
- selected log availability and safe content checks;
- supported read-only SQLite access and basic state consistency;
- filesystem permissions or accessibility needed to explain an unavailable surface; and
- clear reporting of optional or unsupported surfaces.

The complete and current category list, limits, and semantics are in the public matrix: https://github.com/AtlasOmnia/hermes-health-improvement-loops/blob/main/docs/health-check-matrix.md

Do not turn a missing optional file into a repair request. Do not expand a bounded probe into a recursive crawl. Do not copy credentials, authentication material, private memories, raw transcripts, or personal profiles into a report.

### 5. Run the improvement lane

Provide one explicit outcome packet or fixture file. The improvement lane evaluates that supplied material; it does not discover more. Confirm that the packet is the intended input, is suitable for the review boundary, and has been redacted or otherwise prepared according to the public implementation’s current rules.

The evaluator applies the current rubric to the supplied outcomes and may identify a notable, repeated, or actionable pattern. It emits a suggestion or review finding, not an automatic change. Keep the packet’s provenance visible enough for a reviewer to understand what was evaluated, without exposing sensitive content unnecessarily.

### 6. Keep runtime state external

Write package-owned runtime artifacts only to an explicit external runtime directory supported by the implementation. Separate source, selected Hermes home, outcome packet, and runtime artifacts conceptually and physically where practical. A package ledger or suggestion history is not Hermes configuration and must not be placed into Hermes configuration merely because both are local files.

If a default runtime location is offered by the implementation, verify it from current documentation and treat it as an implementation detail—not as a substitute for a clearly scoped runtime boundary in a sensitive audit.

### 7. Produce an optional report

A report can place the independently produced health result and improvement result side by side. It must preserve lane identity, input provenance, run identifiers supplied by the implementation, and failure state. It must not imply that the health lane validated the improvement lane, that the improvement lane discovered health evidence, or that either lane approved a change.

If either lane fails, is unavailable, or is unknown, the report must preserve that state. Do not summarize a mixed report as healthy because one section passed.

### 8. Stop at the review gate

Deliver the result for human review. If the reviewer wants a change, open a new, separately scoped Hermes task with an explicit target, allowed files or settings, rollback plan, and verification plan. Load `hermes-agent`, inspect current help and documentation, and apply the appropriate mutation gates for that new task.

Do not let a health audit or suggestion evaluator call a second agent to perform an unapproved fix, create a cron job, change a provider or model, alter delivery, restart a service, or publish a report.

## Interpreting results

### Status vocabulary

Use the public implementation’s exact status vocabulary and preserve its distinctions. In ordinary language, the following principles apply:

- **Healthy** means the specific check ran, its required evidence was available, and the defined invariant passed. It does not mean all of Hermes is healthy.
- **Warning** means the check ran and found a condition that deserves attention, but the result is not necessarily a failure or authorization to act.
- **Unavailable** means the check could not inspect a required surface because it was missing, inaccessible, unsupported in the current environment, or otherwise unavailable. It is not a pass.
- **Unknown** means the available evidence was insufficient or ambiguous. It is not a pass.
- **Failed or error** means the check or evaluation could not complete as specified. Do not downgrade it to warning merely to make a report look clean.
- **Not observed or not applicable** means the check was intentionally outside the requested scope. It is not a positive health assertion.

Never call an unknown, unavailable, unobserved, unsupported, malformed, stale, or errored status healthy. Never convert a missing optional surface into a silent success. A partial report must say which checks ran and which did not.

### Layered failure model

Classify failures by where they occurred. This prevents a clean-looking output from hiding a broken execution path.

1. **Pre-dispatch or configuration layer** — the request, explicit home, packet, manifest, arguments, or configuration was invalid, incomplete, ambiguous, or rejected before the lane ran. Examples include missing required input, an invalid path boundary, an unsupported option, or a manifest validation failure.
2. **Execution layer** — the lane started but could not complete its bounded read or evaluation. Examples include a read error, parse failure, permission problem, timeout, database access failure, or unexpected implementation exception.
3. **External side-effect layer** — an action outside the read-only/audit contract was requested or attempted, such as writing Hermes state, changing configuration, creating a scheduler entry, modifying a delivery route, or applying a suggestion. This playbook treats such work as out of scope unless separately approved; a renderer’s success does not prove an external side effect occurred.
4. **Delivery layer** — the result was produced but could not be stored, returned, shared, or otherwise delivered to the intended review surface. A delivery failure does not turn the underlying check into a health pass.

Report the earliest and most specific layer supported by evidence. A pre-dispatch rejection is not an execution failure. An execution failure is not a healthy result. A delivery failure is not proof that the audit did not run, but it is also not proof that the reviewer received the result. If the layer is ambiguous, classify it as unknown and preserve the raw bounded evidence for review.

### Evidence before conclusions

Separate these statements:

- the request was accepted;
- the lane executed;
- a specific check passed;
- a result was written to external runtime state;
- a result was delivered to a reviewer; and
- a human approved a next action.

Each is a different claim. Confirm each from the appropriate output or runtime evidence. Process exit zero alone is not proof of a healthy Hermes installation, an installed scheduler entry, a delivered report, or an approved improvement.

### Suggestions are hypotheses

Treat every improvement suggestion as a hypothesis anchored to the supplied outcome packet and current rubric. Check whether the evidence is representative, whether the fingerprint is genuinely repeated, whether the proposed scope matches the evidence, and whether the suggestion conflicts with a known safety boundary. A suggestion may be useful even when it is not yet actionable; it remains non-authoritative until a human reviews it.

## Common Pitfalls

1. **Using an implicit Hermes home.** An audit against the wrong home can be internally consistent and still irrelevant. Require an explicit operator-selected home and record the target boundary.

2. **Treating the health lane as a repair tool.** Health is observation. Do not restart, prune, rewrite, migrate, or reconfigure merely because a check reports warning or unavailable.

3. **Letting improvement discover its own evidence.** The improvement lane accepts an explicit packet. Do not add transcript crawling, session searching, memory inspection, or recursive source discovery.

4. **Copying the implementation into this skill.** The companion playbook should remain stable and concise. Link to the public project and current matrix for executable details, limits, and inventory.

5. **Calling unknown healthy.** Missing evidence, permission failures, malformed data, unsupported surfaces, and ambiguous outcomes must remain visibly non-healthy.

6. **Confusing a dry run with installation.** A rendered manifest or proposal proves only that inputs were rendered. It does not prove that a scheduler, configuration, service, route, or delivery target changed.

7. **Using remembered CLI syntax.** Hermes command surfaces evolve. Inspect the installed command’s current help before rendering operational commands, especially scheduler-related commands.

8. **Choosing neutral-sounding defaults.** “Default provider,” “standard model,” “usual delivery,” or “local route” can still be consequential choices. Keep model, provider, route, host, transport, schedule, and delivery values explicit and operator-supplied.

9. **Mixing lane failures.** A failed improvement evaluation must not be hidden by a passing health result, and a health read failure must not be represented as an improvement suggestion.

10. **Writing runtime artifacts into Hermes.** External package ledgers and reports are not Hermes skills, configuration, sessions, or scheduler state. Keep them in an external runtime directory.

11. **Treating redaction as proof of privacy.** Review packets and reports before sharing. Redaction is a safeguard with limitations, not a guarantee that all personal or secret-like data is absent.

12. **Letting a suggestion trigger automation.** No suggestion should silently create a scheduler entry, modify a skill, change a provider or model, alter delivery, restart a service, or publish a report. Require a new approval boundary.

13. **Using a stale matrix.** The check inventory changes with the public implementation. Read the current matrix when a result depends on a particular check, limit, or status meaning.

14. **Reporting only the final message.** Preserve enough structured evidence to distinguish dispatch rejection, execution failure, external side-effect refusal or attempt, and delivery failure. A polished summary cannot repair missing provenance.

15. **Assuming an optional report validates everything.** A combined report is a view over independent results. It does not add checks, fix failures, or establish a global health claim.

## Verification Checklist

- [ ] The request was classified as health, improvement, optional report, or a separately approved mutation.
- [ ] The selected Hermes home was explicit and bounded for health work.
- [ ] The improvement input was an explicit outcome packet or fixture; no source discovery was added.
- [ ] The public project and current health-check matrix were consulted when implementation details mattered.
- [ ] `hermes-agent` was loaded before any Hermes change or operational advice that could mutate Hermes.
- [ ] Current Hermes CLI help was consulted before rendering any operational or scheduler command.
- [ ] Dry-run or manifest rendering was used when available before any separately approved apply step.
- [ ] Health and improvement were executed and interpreted as separate lanes.
- [ ] Runtime artifacts, if any, were written only to an external package-owned runtime location.
- [ ] Every status was preserved accurately; unknown, unavailable, unobserved, malformed, stale, and errored results were not called healthy.
- [ ] Failures were classified as pre-dispatch/configuration, execution, external side-effect, or delivery failures where applicable.
- [ ] Any combined report preserved lane identity and did not imply extra authority.
- [ ] Suggestions were presented as human-review-only hypotheses.
- [ ] No configuration, scheduler, provider, model, route, host, transport, delivery, credential, or Hermes-home mutation was performed under this playbook.
- [ ] A separately scoped follow-up is required before any implementation, experiment, scheduling, publication, or other mutation.
