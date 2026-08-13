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
    related_skills: [hermes-agent]
---

# Hermes Health Improvement Loops

## Overview

This public operating playbook explains safe use and interpretation of the Hermes Health Improvement Loops companion project. It is not the executable implementation, a copied check inventory, Hermes documentation, or authority to change Hermes.

Public sources of truth:

- Project: https://github.com/AtlasOmnia/hermes-health-improvement-loops
- Current health-check matrix: https://github.com/AtlasOmnia/hermes-health-improvement-loops/blob/main/docs/health-check-matrix.md

Use the public project and matrix for exact implementation behavior, supported surfaces, limits, schemas, release changes, and implementation-level verification. This skill routes code-level detail and the exact inventory to those sources rather than duplicating them. If this playbook and the public project differ, consult the current public implementation and matrix, while still applying this safety boundary.

The project has two independent lanes:

- **Health:** bounded, read-only checks against an operator-selected Hermes home.
- **Improvement:** evaluation of one explicitly supplied outcome packet, producing a suggestion for human review.

An optional report may display already-produced results together. Presentation does not join the lanes’ inputs, discovery, credentials, runtime authority, configuration control, scheduler control, or delivery authority. This skill is generic: it chooses no model, provider, route, host, transport, schedule, delivery target, profile, account, or default home, and contains no credentials or private operating procedure.

## When to Use

Use this skill to:

- perform a bounded Hermes health audit without changing the installation;
- understand whether a supported surface is healthy, degraded, unavailable, unknown, or not observed;
- evaluate explicit outcomes for a repeated failure or quality pattern;
- prepare a review packet for possible improvement work;
- inspect the public matrix to understand available evidence; or
- explain why an improvement suggestion must not automatically change Hermes.

Do not use it as authority to change Hermes configuration, skills, memory, sessions, scheduler state, credentials, providers, models, routes, hosts, or delivery; discover or crawl unsupplied outcome sources; treat health as permission to repair, restart, reconfigure, or publish; treat a suggestion as an approved change; replace current CLI help with remembered syntax; or call a missing, inaccessible, malformed, stale, unsupported, or ambiguous surface healthy.

If implementation, mutation, scheduling, or publication is requested, stop at that boundary and obtain separately scoped approval. Before any Hermes mutation or operational advice that could mutate Hermes, load `hermes-agent`, consult current Hermes documentation, and verify the live command surface. This companion project remains read-only/audit and suggestion-only unless a separately reviewed and authorized integration says otherwise.

## Safety and authority boundary

### Authority levels

Apply these levels in order:

1. **Observation:** read bounded, permitted data from an explicit operator-selected Hermes home or explicit outcome packet.
2. **Evaluation:** classify observed evidence or evaluate a redacted packet under current project rules.
3. **Suggestion:** describe a possible improvement for a person to review.
4. **Mutation:** change Hermes, its configuration, its scheduler, or an external system. This skill grants none.

Normal operation stops at suggestion authority. A health check, repeated outcome, or report never grants mutation authority. A person must make the separate decision, define the exact target and allowlist, authorize the mutation, and use the appropriate Hermes procedure.

### Read-only health

Health may inspect only bounded, supported surfaces through the public implementation. It must not write to the selected Hermes home, update files in place, alter a database, prune history, rotate credentials, restart a service, create scheduler state, or repair a condition. If a tool or wrapper unexpectedly attempts a write, treat that as a failure and stop; do not broaden authorization.

Require an explicit operator-selected Hermes home. Do not silently substitute a default, search other homes, recursively crawl unrelated paths, or turn a missing optional file into a repair request. Keep the probe bounded and preserve which surfaces were observed.

### Suggestion-only improvement

Improvement consumes only one explicitly supplied outcome packet or fixture. It must not search a Hermes home, crawl transcripts, infer private sources, harvest memory, search sessions, or silently broaden its input set. Review the packet for sensitivity. Redaction reduces exposure; it does not prove that every personal or secret-like value was removed.

The evaluator may identify a notable, repeated, or actionable pattern under the current public rubric. Its output is a suggestion or review finding, never a patch, approval, schedule, deployment, release, rollback, or automatic change. Keep enough provenance for review without exposing unnecessary sensitive content.

### Human-only review

A human must review the evidence, classification, proposed direction, affected boundary, and expected risk before any experiment or change. The reviewer decides whether to reject, defer, investigate, or authorize a separately scoped mutation. No suggestion may trigger an agent, scheduler, configuration or skill edit, provider/model change, route/delivery change, restart, or publication.

A human must also decide whether a report is appropriate to share. Reports can contain operational facts even when redaction is enabled. Never publish a raw report merely because a command completed successfully.

### Hermes guidance and current CLI help

Before changing Hermes, installed skills, configuration, scheduler, or runtime, load `hermes-agent` and consult current Hermes documentation. Verify the live command surface rather than relying on this playbook or remembered syntax.

For any separately approved task that renders or proposes a Hermes command, inspect current CLI help for the installed version and relevant subcommand first. Render only syntax confirmed by that help. This skill intentionally does not freeze scheduler flags or provide a cron recipe. Current help is required before command rendering, even when a command appears obvious or low risk.

## Operating flow

Keep health and improvement as two transactions with separate inputs, permissions, evidence, and failure handling.

### 1. Establish the boundary

Confirm that the request is an audit, evaluation, or report—not an instruction to repair Hermes. Identify the explicit operator-selected Hermes home for health, the explicit outcome packet for improvement, and an external runtime destination for package-owned outputs if needed.

If the target or packet is absent, report the missing input and stop that lane. Do not substitute an implicit home, guessed packet, session search, transcript crawl, live source, or other discovery. Record one lane before execution:

- `health`: selected home, bounded read-only probe, and external result destination if applicable;
- `improvement`: explicit packet, redaction/evaluation, and external result destination if applicable; or
- `report`: already-produced health and improvement results, with no new authority.

### 2. Inspect the current public contract

Open the current public health-check matrix before interpreting a result that depends on a particular check. It is the authoritative inventory of supported categories, inputs, limits, and expected statuses. Do not copy implementation-level inventory into this skill or treat an old report or prompt as current.

Inspect current Hermes CLI help whenever a task touches command syntax. Help is version-sensitive. Do not render a scheduler, installation, or other operational command from memory when current help can answer it.

### 3. Render before applying anything

If the public implementation offers a manifest or setup renderer, use dry-run or render-only mode first. The safe default is a reviewable manifest or command proposal without changing Hermes files or creating scheduler state.

A rendered manifest is an inspection artifact. It does not prove a job was installed, a service is running, or an external action succeeded. Verify its inputs and boundaries before considering any separately approved next step. Model, provider, delivery, schedule, route, host, and similar values remain explicit operator inputs; this skill chooses none of them.

### 4. Run the health lane

Run the bounded health audit only against the explicit Hermes home. Use the public implementation and current matrix for the complete check inventory, limits, and semantics. Typical evidence may include metadata, bounded structured-state parsing, selected log checks, supported read-only SQLite access, and accessibility needed to explain an unavailable surface; these examples do not replace the matrix.

Do not expand a bounded probe into a recursive crawl. Do not copy credentials, authentication material, private memories, raw transcripts, or personal profiles into a report. Do not turn a warning or unavailable result into an instruction to repair.

### 5. Run the improvement lane

Provide one explicit outcome packet or fixture. Confirm that it is the intended input, suitable for the review boundary, and prepared according to the public implementation’s current rules. The lane evaluates only that supplied material.

Preserve enough provenance for review without unnecessary sensitive content. Treat every suggestion as a hypothesis anchored to the packet and current rubric. Check that the evidence is representative, the fingerprint genuinely repeated, the proposed scope matches the evidence, and the suggestion does not conflict with a safety boundary. It remains non-authoritative until human review.

### 6. Keep runtime state external

Write package-owned ledgers, reports, or other runtime artifacts only to an explicit external runtime directory supported by the implementation. Keep source, selected Hermes home, outcome packet, and runtime artifacts separate where practical. A package ledger or suggestion history is not Hermes configuration and must not be placed into Hermes configuration.

If a default runtime location is offered, verify it from current public documentation and treat it as an implementation detail—not permission to write elsewhere or a substitute for a scoped sensitive-audit boundary.

### 7. Produce an optional report

A report may place independently produced health and improvement results side by side. Preserve lane identity, input provenance, implementation-supplied run identifiers, and failure state. It must not imply that health validated improvement, improvement discovered health evidence, or either lane approved a change.

If either lane fails, is unavailable, or is unknown, preserve that state. Never summarize a mixed report as healthy because one section passed. A report is presentation only and adds no authority.

### 8. Stop at human review

Deliver the result for human review. If the reviewer wants a change, open a new, separately scoped Hermes task with an explicit target, allowed files or settings, rollback plan, and verification plan. Load `hermes-agent`, inspect current documentation and CLI help, and apply the appropriate mutation gates for that new task.

## Interpreting results

### Status vocabulary

Use the public implementation’s exact vocabulary and preserve its distinctions:

- **Healthy:** the specific check ran, required evidence was available, and its invariant passed. It is not a claim that all Hermes is healthy.
- **Warning:** the check ran and found a condition needing attention. It is not a failure or authorization to act.
- **Unavailable:** a required surface could not be inspected because it was missing, inaccessible, unsupported, or otherwise unavailable. It is not a pass.
- **Unknown:** available evidence was insufficient or ambiguous. It is not a pass.
- **Failed or error:** the check or evaluation could not complete as specified. Do not downgrade it to make a report look clean.
- **Not observed or not applicable:** the check was outside the requested scope. It is not a positive health assertion.

Unknown, unavailable, unobserved, unsupported, malformed, stale, or errored results are non-healthy. Never silently convert missing optional evidence into success. A partial report must say which checks ran and which did not.

### Layered failure model

Classify failures by where they occurred so a clean-looking output cannot hide a broken path:

1. **Pre-dispatch/configuration:** the request, explicit home, packet, manifest, arguments, or configuration was invalid, incomplete, ambiguous, or rejected before the lane ran. Examples: missing input, invalid boundary, unsupported option, or manifest validation failure.
2. **Execution:** the lane started but could not complete its bounded read or evaluation. Examples: read or parse error, permission problem, timeout, database failure, or implementation exception.
3. **External side-effect:** work outside the audit/suggestion contract was requested or attempted, such as writing Hermes state, changing configuration, creating scheduler state, modifying delivery, or applying a suggestion. Treat it as out of scope unless separately approved. Renderer success does not prove a side effect occurred.
4. **Delivery:** a result was produced but could not be stored, returned, shared, or delivered to the intended review surface. Delivery failure does not make the underlying result healthy or prove that a reviewer received it.

Report the earliest and most specific layer supported by evidence. A pre-dispatch rejection is not an execution failure; execution failure is not healthy; delivery failure is not proof that the audit did not run. If the layer is ambiguous, classify it as unknown and preserve bounded evidence for review.

### Evidence before conclusions

Keep these claims separate and verify each from appropriate evidence: the request was accepted; the lane executed; a specific check passed; a result was written to external runtime state; a result was delivered to a reviewer; and a human approved a next action. Process exit zero alone proves none of these beyond the process’s own reported completion.

## Common Pitfalls

1. **Implicit Hermes home:** require an explicit operator-selected home and record its boundary.
2. **Health as repair:** do not restart, prune, rewrite, migrate, or reconfigure because a check is warning or unavailable.
3. **Improvement discovers evidence:** accept only an explicit packet; do not add transcript crawling, session search, memory inspection, or source discovery.
4. **Copied implementation detail:** use the public project and current matrix for exact behavior, limits, and inventory.
5. **Unknown called healthy:** missing evidence, permission failures, malformed data, unsupported surfaces, and ambiguity remain non-healthy.
6. **Dry run confused with installation:** rendering proves only that inputs were rendered, not scheduler, configuration, service, route, or delivery changes.
7. **Remembered CLI syntax:** load `hermes-agent` before Hermes mutations and inspect current CLI help before rendering operational commands.
8. **Consequential defaults:** do not choose a provider, model, route, host, transport, schedule, delivery target, profile, account, or private location.
9. **Mixed lane failures:** a passing health result cannot hide failed improvement, and a health read failure is not an improvement suggestion.
10. **Runtime artifacts in Hermes:** external ledgers and reports are not skills, configuration, sessions, or scheduler state.
11. **Redaction treated as proof:** review packets and reports before sharing; redaction is a safeguard, not a guarantee.
12. **Suggestion triggers automation:** require a new approval boundary before experiment, mutation, schedule, restart, delivery change, or publication.
13. **Stale matrix:** read the current matrix whenever a result depends on a check, limit, or status meaning.
14. **Only the final message reported:** preserve evidence distinguishing pre-dispatch/configuration, execution, external-side-effect, and delivery failures.
15. **Combined report treated as validation:** it is only a view over independent results and adds no checks or authority.

## Verification Checklist

- [ ] Request classified as health, improvement, optional report, or separately approved mutation.
- [ ] Selected Hermes home explicit and bounded for health.
- [ ] Improvement input explicit outcome packet or fixture; no source discovery.
- [ ] Public project and current matrix consulted when implementation details mattered.
- [ ] `hermes-agent` loaded before any Hermes mutation or mutation-capable operational advice.
- [ ] Current Hermes CLI help consulted before rendering any operational or scheduler command.
- [ ] Dry-run or manifest rendering used when available before a separately approved apply step.
- [ ] Health and improvement executed and interpreted as separate lanes.
- [ ] Runtime artifacts, if any, written only to an external package-owned runtime location.
- [ ] Unknown, unavailable, unobserved, malformed, stale, and errored results not called healthy.
- [ ] Failures classified as pre-dispatch/configuration, execution, external side-effect, or delivery where applicable.
- [ ] Combined report preserved lane identity and added no authority.
- [ ] Suggestions presented as human-review-only hypotheses.
- [ ] No Hermes-home, configuration, scheduler, provider, model, route, host, transport, delivery, credential, profile, account, or publication mutation performed under this skill.
- [ ] Separately scoped follow-up required before implementation, experimentation, scheduling, publication, or any other mutation.
