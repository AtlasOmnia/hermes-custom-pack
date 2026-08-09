---
name: telegram-agent-to-agent
description: Use when setting up two Hermes agents (or any two agents) to talk to each other over a Telegram group. Covers BotFather setup, gateway mention config, the literal-mention handoff protocol, and the anti-loop rules (ack suppression, bounded retries, hold semantics) that keep agent pairs from ping-ponging.
version: 1.0.0
author: AtlasOmnia
license: MIT
platforms:
  - linux
  - macos
  - windows
metadata:
  hermes:
    tags:
      - telegram
      - agent-to-agent
      - a2a
      - messaging
      - gateway
      - orchestration
      - multi-agent
    related_skills:
      - hermes-agent
---
# Telegram Agent-to-Agent Bridge

## Overview

Two Hermes agents on different machines can communicate through a **Telegram group** instead of SSH, remote APIs, or shared drives. The group is the transport *and* the audit log: every handoff is visible to the human, nothing is hidden in a shell session, and the agents only act when addressed by their literal bot mention.

This skill gives you the complete setup — two bots, one group, gateway configuration — plus the **protocol and anti-loop rules** that keep the pair from spiraling into infinite acknowledgment ping-pong. The rules here are the ones that have proven necessary in production agent-to-agent deployments: literal-mention addressing, acknowledgment suppression, bounded retries, and hold semantics.

## When to Use

Use when:

- setting up agent-to-agent communication over Telegram for the first time;
- two Hermes gateways (different machines, different bots) must exchange work handoffs;
- agents keep replying to each other in loops or ack storms and you need to stop it;
- handoffs must be human-visible and auditable;
- you want a transport with no SSH surface exposed.

Do not use when:

- both agents run on the same machine — use local orchestration instead;
- the human has explicitly allowed a direct SSH/API route and Telegram is not required;
- the payloads contain secrets — Telegram messages are not encrypted end-to-end in groups;
- one agent is not a bot (a human or a different platform) — adapt the mention protocol accordingly.

## Architecture

```text
Machine A                          Machine B
┌──────────────────┐               ┌──────────────────┐
│ Hermes gateway A │               │ Hermes gateway B │
│ bot = @Agent_A   │               │ bot = @Agent_B   │
│ require_mention  │               │ require_mention  │
└────────┬─────────┘               └────────┬─────────┘
         │  Telegram Bot API (polling)      │
         └──────────────┬───────────────────┘
                        ▼
              ┌─────────────────────┐
              │  Telegram group     │
              │  @Agent_A, @Agent_B │
              │  + the human        │
              └─────────────────────┘
```

Each gateway only *acts* on messages that literally mention its own bot. Everything else is observed context. The human can interject at any point and both agents can read the full history.

## Part 1 — Bots and group setup

1. **Create two bots** with [@BotFather](https://t.me/BotFather) (`/newbot`). Name them clearly (`@Agent_A`, `@Agent_B`).
2. **Disable privacy mode on both bots**: BotFather → `/setprivacy` → **Disable**. With privacy enabled, a bot only receives messages that mention it, start with `/`, or reply to its own message. Disabling it makes the group fully visible to both agents and is required for reliable "observed context" behavior.
3. **Create a group**, add both bots and the human(s). Bots do not need to be admins.
4. **Get the group chat ID.** Send one message in the group, then fetch updates from each bot:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```
   The ID appears as `"chat":{"id":-100...}`. Note that groups often migrate to supergroups, which **changes the chat ID** to a `-100`-prefixed value. Use the latest ID you observe.
5. Keep both bot tokens in each machine's Hermes `.env` (e.g. `TELEGRAM_BOT_TOKEN=<token>`). Never paste tokens into chat, config files, or the group.

## Part 2 — Gateway configuration (both machines)

On each machine, in the Hermes `config.yaml`:

```yaml
telegram:
  allow_bots: mentions          # bots may trigger the agent, but only via mention
  require_mention: true         # never respond to unaddressed messages
  exclusive_bot_mentions: true  # only YOUR bot's mention triggers (not the other bot's)
  allowed_chats: '-1001234567890'  # the group chat ID; nothing else can reach the agent
  observe_unmentioned_group_messages: true  # optional: read the room without acting
```

Reliability hardening for agent-to-agent channels:

```yaml
streaming:
  enabled: false                # send complete messages only; avoids partial-preview artifacts
```

`streaming: false` means each reply arrives whole rather than as an edit-progress preview. On agent channels that matters: a partially delivered receipt looks exactly like a real truncation.

**Restart the gateway after any config change** — the gateway reads config at startup.

## Part 3 — The handoff protocol

These rules govern every agent-to-agent message. Encode them in the agents' system prompt or a skill file on both sides.

1. **Literal mention first.** An outbound message to the other agent must begin with the other bot's `@username` as the very first characters — no label, punctuation, emoji, or Markdown before it. Saying the name in prose does not count.
2. **Reciprocal rule.** Replies back must begin with *your* bot's `@username` first.
3. **Test/informational messages** carry the marker `DO NOT EXECUTE` and ask for a bounded receipt (e.g. "Reply only: RECEIVED").
4. **Work messages are self-contained**: objective, scope, current evidence, exact requested action, approval gates. The receiving agent must be able to act without reading a separate thread.
5. **Plain text only.** No audio, TTS, images, or attachments between agents.
6. **Verify in the channel.** Confirm (a) your sender-labeled message actually posted, and (b) the other agent's sender-labeled in-channel receipt. A successful API/SSH call is not Telegram evidence.

## Part 4 — Anti-loop rules

These are the rules that stop agent pairs from burning tokens on each other:

1. **Acknowledgment suppression (the #1 rule).** Never reply to acknowledgment-only messages ("Understood", "Received", "RECEIVED", "OK", "noted"). After either side acknowledges a receipt, a hold, or a no-action state, **both sides go silent** until a new substantive request or fresh evidence arrives.
2. **No self-echo.** Never respond to your own bot's messages. Some gateway configurations deliver your own sends back into the session — gate on the sender.
3. **Mention-gated acting.** Only act on messages that literally mention your bot. Treat every other message as observed context; do not reply to it.
4. **One bounded retry.** If a transport attempt fails, retry exactly once with the same content, then stop and report the blocker. Do not escalate to SSH/API/another channel unless the human explicitly changes the transport requirement.
5. **Terse acks, no meta-commentary.** Acknowledgments are one word. No summarizing what you'll do next, no "I'll wait here", no status narration — that narration is what becomes a loop.
6. **Respect flood control.** On a `429` flood error, back off (the gateway retries with backoff); never manually resend in a hurry.
7. **Hold semantics.** A HOLD, receipt, or "no action" message ends the exchange. Resumption requires a new substantive message or an explicit human instruction.
8. **Receipts are not evidence.** A receipt confirms *delivery*, not *work done*. Work results must arrive with the evidence that supports them, in the same exchange.

## Common Pitfalls

1. **Bots never see each other.** Privacy mode is still ON. Fix: BotFather → `/setprivacy` → Disable, for both bots.
2. **Ack-storm loops.** Missing acknowledgment suppression. Add rule 1 and verify with a test ack.
3. **Agent ignores a message that "obviously" addresses it.** The prefix protocol was violated — message began with prose, a bold label, or punctuation instead of the literal `@username`. Fix the sender side, not the receiver.
4. **Wrong chat ID after migration.** "Group migrated to supergroup. New chat id: -100…" in the logs means Telegram changed the ID. Update `allowed_chats` and restart.
5. **Partial messages ending with a `▉` cursor.** Streaming preview artifacts. Set `streaming.enabled: false` and restart; treat a partial as *not* delivered until the complete text arrives.
6. **Both bots answer one message.** `exclusive_bot_mentions: true` is missing, or the message mentions both bots. Only mention the intended recipient.
7. **Config changes "not working".** The gateway holds config at startup — restart after every change.
8. **Loop of "did you get it?" / "yes".** That is exactly the acknowledgment loop; the fix is silence, not a better ack format.

## Verification Checklist

- [ ] Both bots exist, both have privacy mode disabled
- [ ] Group contains both bots and the human; chat ID recorded from `getUpdates`
- [ ] `allowed_chats`, `require_mention`, `allow_bots: mentions`, `exclusive_bot_mentions` set on **both** gateways; gateways restarted
- [ ] `streaming.enabled: false` set on both (reliability)
- [ ] A→B test: message starting with `@Agent_B DO NOT EXECUTE …` is observed by B's gateway (check B's gateway log)
- [ ] B replies starting with `@Agent_A`; the reply is visible in the group
- [ ] Ack test: B sends `RECEIVED`; A does **not** reply (no loop)
- [ ] A long evidence message arrives complete — no `▉` cursor, no truncation
- [ ] The full exchange is readable by the human in the group

## Reference files

- `templates/telegram-a2a-config.yaml` — annotated gateway config for both sides.
