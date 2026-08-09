# Telegram Agent-to-Agent Bridge for Hermes Agent

Let two Hermes agents on different machines talk through a Telegram group — with the protocol rules that keep them from looping forever.

![Telegram A2A bridge diagram](https://raw.githubusercontent.com/AtlasOmnia/hermes-agent-custom-pack/main/assets/telegram-agent-to-agent.svg)

The group is the transport **and** the audit log: every handoff is visible to the human, agents act only when addressed by their literal bot mention, and a set of anti-loop rules (acknowledgment suppression, one bounded retry, hold semantics) stops acknowledgment ping-pong before it starts.

## What it includes

- `SKILL.md` — installable Hermes workflow with setup, protocol, and anti-loop rules
- `templates/telegram-a2a-config.yaml` — annotated gateway config for both sides

No scripts or third-party packages required. You only need two bot tokens from [@BotFather](https://t.me/BotFather) and one Telegram group.

## What you'll have after setup

1. **Two bots** (`@Agent_A`, `@Agent_B`) with privacy mode disabled
2. **One group** containing both bots and you
3. **Both gateways configured**: mention-gated (`require_mention`, `allow_bots: mentions`, `exclusive_bot_mentions`), scoped to the group only (`allowed_chats`), complete-message delivery (`streaming.enabled: false`)
4. **The protocol in both agents' instructions**: literal `@username` first, `DO NOT EXECUTE` for tests, self-contained work messages, in-channel verification
5. **The anti-loop rules in both agents' instructions**: ack suppression, no self-echo, one bounded retry, hold semantics

## Install

Install the agent instructions only:

```bash
hermes skills install https://raw.githubusercontent.com/AtlasOmnia/hermes-agent-custom-pack/main/skills/telegram-agent-to-agent/SKILL.md
```

For the config template, copy the full package:

macOS/Linux:

```bash
curl -O https://raw.githubusercontent.com/AtlasOmnia/hermes-agent-custom-pack/main/skills/telegram-agent-to-agent/templates/telegram-a2a-config.yaml
```

Windows PowerShell:

```powershell
Invoke-WebRequest -OutFile telegram-a2a-config.yaml https://raw.githubusercontent.com/AtlasOmnia/hermes-agent-custom-pack/main/skills/telegram-agent-to-agent/templates/telegram-a2a-config.yaml
```

## One-time setup (summary)

1. Create two bots with @BotFather; run `/setprivacy` → **Disable** on both.
2. Create a group; add both bots and yourself.
3. Send a message in the group, read the chat ID from `getUpdates` (look for `-100…`).
4. Put each token in its machine's `.env` as `TELEGRAM_BOT_TOKEN`.
5. Apply the config template on both machines; restart both gateways.
6. Run the verification checklist in `SKILL.md` (mention test, ack-loop test, long-message test).

## Design notes

- **Mention-gated acting** (`exclusive_bot_mentions: true`) is what lets both agents share one group without stepping on each other.
- **Acknowledgment suppression** is the single most important anti-loop rule: after an ack, both sides stay silent until a substantive message arrives. Loops are almost always ack loops.
- **`streaming.enabled: false`** on agent channels avoids the partial-preview-with-cursor artifact that looks exactly like message truncation.
- **One bounded retry, then report** — no escalating fallback to SSH/API unless the human changes the transport requirement.

## License

MIT. No workspace IDs, chat IDs, bot handles, credentials, or private infrastructure are included in this package — every installation discovers its own.
