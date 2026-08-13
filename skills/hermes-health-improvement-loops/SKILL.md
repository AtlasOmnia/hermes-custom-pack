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

This public playbook covers safe use and interpretation of the Hermes Health Improvement Loops companion project. It is not the implementation, a copied check inventory, Hermes documentation, or authority to change Hermes.

Public sources of truth:

- Project: https://github.com/AtlasOmnia/hermes-health-improvement-loops
- Matrix: https://github.com/AtlasOmnia/hermes-health-improvement-loops/blob/main/docs/health-check-matrix.md

Use those sources for exact behavior, supported surfaces, limits, schemas, release changes, and implementation verification. This skill routes code-level detail and the exact inventory there instead of duplicating them. If sources differ, consult the current public implementation and matrix while applying this safety boundary.

The project has two independent lanes: **health**, which performs bounded read-only checks against an operator-selected Hermes home, and **improvement**, which evaluates one explicitly supplied outcome packet and produces a suggestion for human review. A report may display existing results together, but never joins their inputs, discovery, credentials, runtime, configuration, scheduler, or delivery authority. This skill chooses no model, provider, route, host, transport, schedule, delivery target, profile, account, or default home.

## When to Use

Use this skill for bounded Hermes health audits, supported-surface status interpretation, evaluation of explicit repeated outcomes, review-packet preparation, current-matrix inspection, or explaining why a suggestion must not automatically change Hermes.

Do not use it to mutate Hermes, discover unsupplied outcome sources, treat health as repair permission, treat a suggestion as approval, use remembered CLI syntax, or call missing, inaccessible, malformed, stale, unsupported, or ambiguous evidence healthy.

If implementation, mutation, scheduling, or publication is requested, stop and obtain separately scoped approval. Before any Hermes mutation or mutation-capable operational advice, load `hermes-agent`, consult current Hermes documentation, and verify the live command surface. The companion project remains read-only/audit and suggestion-only unless separately reviewed and authorized.

## Safety and authority boundary

### Authority levels

1. **Observation:** read bounded data from an explicit Hermes home or outcome packet.
2. **Evaluation:** classify evidence or evaluate a redacted packet under current rules.
3. **Suggestion:** describe a possible improvement for human review.
4. **Mutation:** change Hermes or an external system. This skill grants none.

Normal operation stops at suggestion authority. A check, repeated outcome, or report never grants mutation authority. A person must define the exact target and allowlist, authorize the mutation, and use the proper Hermes procedure.

### Read-only health

Health inspects only bounded, supported surfaces through the public implementation. It must not write to the selected home, update files, alter databases, prune history, rotate credentials, restart services, create scheduler state, or repair a condition. If a tool attempts a write, stop and treat it as failure.

Require an explicit operator-selected home. Do not substitute a default, search other homes, crawl unrelated paths, or turn missing optional evidence into a repair request. Keep the probe bounded and preserve which surfaces were observed.

### Suggestion-only improvement

Improvement consumes only one explicitly supplied outcome packet or fixture. It must not search a Hermes home, crawl transcripts, infer private sources, harvest memory, search sessions, or broaden its input. Review sensitivity first; redaction reduces exposure but does not prove all personal or secret-like values were removed.

The evaluator may identify a pattern under the current public rubric. Its output is a suggestion, never a patch, approval, schedule, deployment, release, rollback, or automatic change. Preserve enough provenance for review without unnecessary sensitive content.

### Human-only review

A human reviews evidence, classification, proposed direction, affected boundary, and risk before any experiment or change, deciding whether to reject, defer, investigate, or authorize a separately scoped mutation. A suggestion may not trigger an agent, scheduler, configuration or skill edit, provider/model change, route/delivery change, restart, or publication.

A human also decides whether a report is shareable. Reports can contain operational facts even with redaction; successful completion is not permission to publish raw output.

### Hermes guidance and current CLI help

Before changing Hermes, installed skills, configuration, scheduler, or runtime, load `hermes-agent`, consult current documentation, and verify the live command surface. For any separately approved command-rendering task, inspect current CLI help for the installed version and relevant subcommand first. Render only syntax confirmed by that help; this skill does not freeze scheduler flags or provide a cron recipe.

## Operating flow

Keep health and improvement as two transactions with separate inputs, permissions, evidence, and failure handling.

### 1. Establish the boundary

Confirm the request is an audit, evaluation, or report—not repair. Identify the explicit operator-selected home, explicit outcome packet, and external runtime destination if needed. If target or packet is absent, report the missing input and stop that lane; never substitute an implicit home, guessed packet, session search, transcript crawl, live source, or other discovery. Record `health`, `improvement`, or `report` before execution.

### 2. Inspect the current contract

Open the current public matrix before interpreting a check-dependent result. It is authoritative for categories, inputs, limits, and statuses; do not copy implementation inventory here or treat old reports as current. Inspect current Hermes CLI help whenever syntax is involved; do not render scheduler, installation, or other operational commands from memory.

### 3. Render before applying

If a manifest or setup renderer exists, use dry-run/render-only first. A rendered proposal is an inspection artifact, not proof of installation, service state, or external success. Verify boundaries before any separately approved step; model, provider, delivery, schedule, route, and host remain explicit operator inputs.

### 4. Run health

Run only against the explicit home. Use the public implementation and matrix for complete inventory, limits, and semantics. Keep probes bounded and read-only; do not recurse, copy credentials, private memories, raw transcripts, or profiles into reports, or turn warning/unavailable into repair.

### 5. Run improvement

Provide one explicit packet or fixture prepared under current public rules. Evaluate only that material, preserve useful provenance, and treat every suggestion as a hypothesis. Check representativeness, repetition, scope fit, and safety conflict; human review remains required.

### 6. Keep runtime external

Write package-owned ledgers, reports, or other artifacts only to an explicit external runtime directory supported by the implementation. Keep source, Hermes home, packet, and runtime separate. A package ledger is not Hermes configuration.

### 7. Report and stop

A report may place independent results side by side while preserving lane identity, provenance, run identifiers, and failure state. It adds no authority. Preserve failure, unavailable, and unknown states; never call a mixed report healthy because one section passed. Deliver for human review. Any desired change requires a new scoped task with target, allowlist, rollback, verification plan, `hermes-agent`, current documentation, and current CLI help.

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

Keep acceptance, execution, check status, external write, delivery, and human approval as separate claims. Verify each from the appropriate evidence; process exit zero alone proves none of them beyond the process’s own completion.

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
