# Community Builds

Skills and workflows built in response to real requests from [r/hermesagent](https://www.reddit.com/r/hermesagent/), mostly from the **Operator Lab** threads, where people describe one task they want Hermes to handle.

Each entry starts from a specific person's request, gets generalized so it works for anyone, and gets tested before it lands here. Nothing in this section contains the requester's private data.

## Index

| Request | Built | Type | Source | Status |
|---|---|---|---|---|
| Reconcile medical bills against insurance EOBs, track deductible and out-of-pocket | [medical-bill-reconciliation](skills/medical-bill-reconciliation/) | Skill + scripts | [Operator Lab #1](https://www.reddit.com/r/hermesagent/comments/1wyimkz/operator_lab_whats_one_real_task_you_want_hermes/) | Ready |
| Turn Plaud meeting notes + calendar into a per-customer timeline with next steps | [plaud-meeting-timeline](workflows/plaud-meeting-timeline.md) | Workflow guide | [Operator Lab #1](https://www.reddit.com/r/hermesagent/comments/1wyimkz/operator_lab_whats_one_real_task_you_want_hermes/) | Draft |
| Get GDScript that drops into a Godot project, on a local model | [godot-gdscript-check-loop](workflows/godot-gdscript-check-loop.md) | Workflow guide | [Operator Lab #1](https://www.reddit.com/r/hermesagent/comments/1wyimkz/operator_lab_whats_one_real_task_you_want_hermes/) | Ready |

## Skills vs workflows

- **`skills/<name>/`** holds installable Hermes skill packages. They follow the same contract as the main [`skills/`](../skills/) collection: `SKILL.md`, `README.md`, optional `scripts/`, `templates/`, `references/`, and `tests/`. They're validated and tested by the same collection scripts.
- **`workflows/<name>.md`** holds step-by-step guides for requests that are mostly setup and good prompting, where a packaged skill would add little. Each guide links its source thread and states where a human stays involved.

When a workflow grows scripts or becomes something people run repeatedly, promote it to a skill.

## Install a community skill

```bash
git clone https://github.com/AtlasOmnia/hermes-agent-custom-pack.git
mkdir -p ~/.hermes/skills/productivity/<skill-name>
cp -R hermes-agent-custom-pack/community/skills/<skill-name>/. ~/.hermes/skills/productivity/<skill-name>/
```

Then start a new Hermes session or run `/reload-skills`. Each skill's README lists any extra dependencies.

## Adding an entry

1. Link the Reddit thread or comment that prompted it. Use the request as written, but leave out usernames, private details, and anything the requester didn't post publicly.
2. Generalize it: placeholders for paths, accounts, providers, and limits.
3. Skills: add tests that use synthetic data only. Workflows: start from [`workflows/_template.md`](workflows/_template.md).
4. Add a row to the index above.
5. Run the checks from the repo root:

```bash
python3 scripts/validate_collection.py
python3 scripts/test_collection.py
```

Workflow guides must include a `**Source thread:**` line and the headings `## Request`, `## Approach`, `## Steps`, `## Human Gates`, and `## Verification`. The validator enforces this.

## Following up

Operator Lab threads come with a follow-up a week later: did it work, fail, or stay blocked? Record what changed in the entry itself, under a dated `## Follow-up` section, so the next person sees what actually happened.
