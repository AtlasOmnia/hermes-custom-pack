# Plaud meeting notes + calendar to a per-customer timeline

**Source thread:** https://www.reddit.com/r/hermesagent/comments/1wyimkz/operator_lab_whats_one_real_task_you_want_hermes/
**Works with:** Plaud (device app or Plaud Desktop) via Plaud MCP, or Zapier as a fallback; Google or Outlook calendar; any notes app that stores Markdown files (Obsidian shown)
**Status:** Draft. Not yet run end to end against a live Plaud account. If you try it, report what breaks in the thread.

## Request

Plaud records and summarizes Teams and Zoom meetings automatically. The goal is for Hermes to pick up those summaries plus the calendar, enrich them, and keep a running timeline and next-step list per customer or project.

## Approach

Plaud has no public API, but it ships Plaud MCP, a read-only MCP server that Plaud recommends for pulling recordings, transcripts, summaries, and action items into other tools ([Plaud support](https://support.plaud.ai/hc/en-us/articles/60726890231449-How-can-I-get-API-access-to-my-Plaud-data)). It is currently free for active Plaud accounts. Hermes loads MCP servers directly, so on a schedule it can list recordings since the last run, read each summary, match it to the calendar event, and append a dated entry to one note per customer or project.

If you would rather have files on disk, Plaud's Zapier trigger can write each summary to a synced folder instead (see Alternative: Zapier).

Plain Markdown files keep the output tool-agnostic: Obsidian, a synced folder, or a Git repo all work. Apple Notes has no file store Hermes can append to without AppleScript or Shortcuts.

## Setup

1. **Plaud MCP.** Requires Node.js 20 or newer. Add the local stdio server to Hermes `config.yaml` and sign in with your Plaud account when prompted ([Plaud MCP docs](https://docs.plaud.ai/plaud-mcp-cli/mcp)):

   ```yaml
   mcp_servers:
     plaud:
       command: npx
       args: ["-y", "@plaud-ai/mcp@latest"]
   ```

   Prefer this local server over Plaud's hosted HTTP endpoint, which routes recording data through Plaud's US server.
2. **Notes folder.** For example `Customers/` for one note per customer or project, plus `Customers/_processed.md` as a ledger of handled Plaud recording ids.
3. **Calendar access.** Connect Google Calendar or Outlook to Hermes through whatever calendar tool or connector the installation uses. Read-only is enough.
4. **Plaud Calendar (Google only, optional).** In the Plaud mobile app, Explore, Integration, Google Calendar. Plaud then names each recording after the matching event and adds attendees and agenda to the summary ([Plaud support](https://support.plaud.ai/hc/en-us/articles/57809292562585-Calendar)). Outlook isn't supported there, so with Outlook Hermes does the time-overlap match itself.
5. **Customer lookup.** Create `Customers/_aliases.md` listing each customer's canonical name, other names it goes by, and attendee email domains:

   ```markdown
   | Canonical | Aliases | Domains |
   |---|---|---|
   | Acme Corp | ACME, Acme Inc | acme.com |
   ```

## Steps

1. Record one test meeting with Plaud Desktop and confirm it shows up through Plaud MCP ("list my recent recordings") the same way device recordings do.
2. Run this once by hand after a meeting:

   > Using Plaud MCP, list recordings since the last date in Customers/_processed.md. Skip any recording id already in the ledger unless its summary changed, in which case update that entry instead of adding a new one. For each new recording, find the calendar event whose time overlaps the recording's start time and duration, and identify the customer or project from the event title and attendee domains using Customers/_aliases.md. Append a dated entry to Customers/<Customer>.md with: meeting title, attendees, 3-5 line summary, decisions, next steps as `- [ ] owner: task (due date)` checkboxes, anything still open from the previous entry, and the Plaud recording id. Add the id to the ledger. If you can't match a customer, don't guess; list it for me.

3. Check the result against the original summary (see Verification). Adjust the prompt until two or three meetings come out right.
4. Save the prompt as a Hermes skill or a cron job that runs at the end of each workday.
5. Add a morning cron:

   > List every unchecked next step across Customers/*.md, grouped by customer, oldest due date first, plus anything due today.

## Alternative: Zapier

In Plaud Web, open Explore, then Integrations, then Zapier ([Plaud support](https://support.plaud.ai/hc/en-us/articles/12200669941647-Zapier-integration)). Create a Zap with the Plaud trigger "Transcript & Summary Ready" and a Google Drive, Dropbox, or OneDrive "Create File From Text" action into a synced `Meetings/Inbox/` folder. A two-step Zap fits Zapier's free plan (100 tasks a month). The trigger also fires on re-transcription and re-summary, so the same meeting can arrive twice; dedupe on the recording title and start time the same way the ledger does above.

## Human Gates

- Review extracted next steps for the first two weeks. Summaries sometimes turn "we should look at" into a commitment.
- Hermes doesn't email or message customers from this workflow.
- Recordings and transcripts include other people's words. Keep the notes private and check your organization's recording and consent policy.

## Verification

- Each meeting appears once, under the right customer or project, with its Plaud recording id.
- Next steps in the customer note match the Plaud summary. Nothing invented, nothing dropped.
- Regenerating a summary in Plaud updates the existing entry rather than adding a second one.
- Unmatched recordings appear in Hermes's report instead of being guessed.

## Common Pitfalls

- **Name drift.** "Acme", "ACME Corp", and `@acme.com` attendees need to resolve to one note. Keep `_aliases.md` current.
- **Back-to-back meetings.** Match on the event whose time overlaps the recording most, not just the nearest start time.
- **Internal meetings.** Add a rule to skip or route meetings with only your own domain.
- **Duplicate entries.** Key everything on the Plaud recording id. Re-summaries and re-runs are normal; the ledger is what keeps them from becoming double entries.
- **Beta terms.** Plaud lists the MCP server as beta and "currently free"; check if it stops working.

## Follow-up

_None yet._
