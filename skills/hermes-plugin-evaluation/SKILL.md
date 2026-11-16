---
name: hermes-plugin-evaluation
description: "Use when vetting a third-party Hermes plugin before install."
version: 1.1.0
platforms:
- macos
- linux
- windows
metadata:
  hermes:
    tags:
    - hermes
    - plugins
    - evaluation
    - security
    - setup
    - pricing
    related_skills:
    - hermes-agent
    - hermes-config-editing
---
# Hermes Plugin Evaluation

## Overview

Evaluate third-party plugins with evidence, keeping code licence, service cost, data flow, and runtime behavior separate. Treat the review as read-only; never equate a temporary Hermes home or capability grant with a security sandbox.

## When to Use

Use this skill before deciding whether to trust, install, enable, or connect a third-party Hermes plugin, portable Agent Plugin, or MCP integration. Produce an evidence-backed go/no-go assessment; evaluation itself is read-only.

## Don't use for

- Authoring or debugging a plugin you own; use the plugin-development workflow.
- Selecting or comparing local models.
- Comparing unrelated marketplace purchases or listings.

## Prerequisites

- Identify the plugin's repository or catalog ID, full source commit, package type, Hermes version, and target platform. A catalog pin displayed in a table may be abbreviated; verify the full commit before treating it as a source boundary.
- Keep the review read-only. Do not run `hermes plugins install` or `hermes plugins enable` as evaluation steps.
- Verify available CLI syntax with `hermes plugins --help` and the relevant `hermes plugins <subcommand> --help` on the target Hermes version.
- Use `web_extract` for public vendor documentation, pricing, privacy, and terms pages. For deeper code review, use `terminal` to clone the exact source revision and verify its commit, then use `read_file` on the clone. Do not execute candidate scripts as part of static inspection.

## Procedure

1. **Locate the catalog entry and exact source.** Use `hermes plugins browse` or `hermes plugins search <term>` to find curated entries. The table includes Tier, Pinned, and Capabilities; current tier values are `official`, `verified`, and `community`. `Pinned` is a short revision label, not necessarily the full commit SHA. Use `hermes plugins info <id>` for the full catalog description and metadata; some entries include a publisher-written `Disclosure` paragraph in that description. Treat it as a claim to verify, not an audit. Browse/search descriptions may be truncated.

   `hermes plugins show <id>` and `hermes plugins capabilities <id>` inspect plugins known to the current runtime, not an uninstalled catalog-only entry. `show` reports details such as status, source, declared emits/listens; `capabilities` compares declared and granted capabilities. These inventories can include bundled plugins as well as user-installed ones.

2. **Inspect the fetched source before any executable check.** Read the repository README/docs, native `plugin.yaml` or portable Agent Plugins v1 `plugin.json`, `mcp.json` or equivalent server declarations, `LICENSE`/`NOTICE`, dependency manifests and lockfiles, setup scripts, registration code, tool and hook handlers, and network/authentication code. Use `read_file` on the clone and cite each relevant relative file path with the reviewed commit. Use `web_extract` for linked vendor pages; do not infer a fact from a link you did not fetch.

3. **Separate code licence, service cost, and data flow.** A public repository is not proof of an open-source licence, and a public/free plugin is not proof that its hosted service is free. Check the actual licence file and vendor pricing/plan pages. Identify paid accounts, API/model use, usage limits, phone/SMS/voice charges, hosting, storage, and paid feature gates. If no pricing page is found or it cannot be fetched, report the service price as unknown—not free.

   Every cost, licence, and data-flow claim in the assessment must cite the URL or fetched repository file that supports it (include the commit for cloned source). Label any claim without a fetched source `UNVERIFIED`; distinguish a publisher's statement from behavior confirmed in code.

4. **Trace behavior and data destinations.** Read the implementation, not just manifest declarations. Review tools, `provides_hooks`, callbacks, startup/setup code, outbound requests, files sent, environment variables, tokens, and inbound webhook/tunnel paths. Hook listeners such as `pre_llm_call` and `post_tool_call` can change gateway behavior and are not merely metadata. `provides_tools` is a declaration, not a restriction on what plugin registration code can add; compare it with `register(ctx)` and the actual runtime surface. Capability grants are a separate consent/audit layer, not a sandbox.

   For MCP-glue plugins, identify the hosted server and trace what it receives for each tool call (including prompts, arguments, URLs, and file contents where applicable). Check the OAuth scopes requested and what those scopes permit. If the server's request handling, retention, pricing, or OAuth details were not fetched, mark them `UNVERIFIED`. When present, read the catalog `Disclosure` through `hermes plugins info <id>`, cite the entry, and compare its claims with the pinned source and provider documentation.

5. **Use runtime gates only after static review.** `hermes plugins doctor <id-or-path>` uses real plugin discovery/registration. `hermes plugins validate <path>` is a catalog-admission check; for a native plugin with `__init__.py`, its capability probe imports the module and invokes its registration path (typically `register(ctx)`; model-provider plugins register at import) in a child process. Both can execute third-party code. A temporary `HERMES_HOME`, subprocess, or blocked socket calls is not an OS security sandbox. Never describe doctor or validate as safe for an unknown package. Run them only after static inspection, preferably in a disposable VM, container, or separate OS account with no secrets and constrained network/filesystem access. `validate --install-deps` also prepares declared dependencies in Hermes's environment; do not use that option for a read-only vetting pass.

6. **Revisit the sign-off when the source changes.** A new plugin commit or catalog pin invalidates the prior code review. For tracked auto-updating installs, `hermes plugins check-updates` is read-only and reports update or `update_url` mismatch state. A changed or newly introduced `update_url` requires review before `hermes plugins trust-update-url <name>`; that command records trust in the new URL and is not a substitute for reviewing it.

## Pitfalls

- Do not equate a public repository, catalog listing, or `Disclosure` paragraph with an independently verified licence, price, or data-flow guarantee.
- Do not call a missing or inaccessible pricing page “free”; use “unknown” and cite what was checked.
- A manifest describes intended capabilities. `register(ctx)` may add runtime tools beyond `provides_tools`; inspect the code and do not treat a declaration or capability grant as a sandbox.
- Hooks can alter model inputs, tool calls, and results without making an external network request. Treat every listener as a behavior change.
- Portable Agent Plugins v1 packages (`plugin.json`) install disabled, but enabling them grants the package's instructions and local executable full trust. Disabled is not sandboxed or inherently safe.
- A temporary Hermes home isolates some application state; it does not prevent filesystem access, subprocess execution, or other activity by code running with the caller's OS privileges.
- MCP glue shifts the review boundary to the server: determine the actual payload and requested OAuth scopes, not just where the thin local wrapper is hosted.
- Any new commit, tag, catalog pin, or trusted update-feed change makes an earlier sign-off stale. Review changed `update_url` values before explicitly trusting them.

## Verification

- [ ] Exact source URL, full commit, package format, Hermes version, and platform are recorded.
- [ ] Licence, dependencies, tools, hooks, setup behavior, network destinations, credentials, MCP payloads, and OAuth scopes were inspected or explicitly marked `UNVERIFIED`.
- [ ] Every cost, licence, and data-flow claim cites a fetched URL or a file path in the reviewed commit; absent pricing is reported as unknown.
- [ ] Marketplace disclosure text, when present, is attributed to its publisher and checked against fetched source/provider evidence.
- [ ] No plugin was installed or enabled as part of evaluation. Any doctor/validate execution followed static review and ran in a disposable OS isolation boundary.
- [ ] Recommendation separates plugin-code licence/cost, external-service cost, data exposure, and operational risk.

## Output contract

Return four concise bullets:

- **Short answer:** free, paid, mixed, or unclear—separately for plugin code and required services.
- **What I verified:** findings with cited URLs or fetched file paths/commit, plus anything labelled `UNVERIFIED`.
- **Cost implication:** licence status, service fees, usage charges, and unknowns.
- **Recommended next step:** a proportionate action based on the evidence and remaining uncertainty.
