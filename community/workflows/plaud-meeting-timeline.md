# Plaud meeting notes + calendar to a per-customer timeline

**Source thread:** https://www.reddit.com/r/hermesagent/comments/1wyimkz/operator_lab_whats_one_real_task_you_want_hermes/
**Works with:** Plaud (desktop or app) with Zapier, Google or Outlook calendar, any notes app that stores Markdown files (Obsidian shown)
**Status:** Ready

## Request

Plaud records and summarizes Teams and Zoom meetings automatically. The goal is for Hermes to pick up those summaries plus the calendar, enrich them, and keep a running timeline and next-step list per customer or project.

## Approach

The hard part isn't Hermes; it's getting Plaud's output somewhere Hermes can read. Plaud's Zapier integration fires when a transcript and summary are ready, so a Zap saves each summary as a file in a notes folder. Hermes then reads that folder and the calendar on a schedule, matches each summary to its meeting, and appends a dated entry to one note per customer.

Plain Markdown files keep this tool-agnostic: Obsidian, a synced folder, or a Git repo all work.

## Setup

1. **Notes folder.** For example `Meetings/Inbox/` for raw summaries and `Customers/` for one note per customer.
2. **Plaud to files.** In Plaud Web, open Explore, then Integrations, then Zapier. Create a Zap with the Plaud trigger "Transcript & Summary Ready" and an action that writes a file to the synced folder: Google Drive, Dropbox, or OneDrive "Upload File" or "Create File From Text". Name the file `YYYY-MM-DD_HHMM_<title>.md`.
3. **Calendar access.** Connect Google Calendar or Outlook to Hermes through whatever calendar tool or connector the installation uses. Read-only is enough.
4. **Customer lookup.** Create `Customers/_aliases.md` listing each customer's canonical name, other names it goes by, and attendee email domains:

   ```markdown
   | Canonical | Aliases | Domains |
   |---|---|---|
   | Acme Corp | ACME, Acme Inc | acme.com |
   ```

## Steps

1. Run this once by hand after a meeting:

   > Read new files in Meetings/Inbox. For each, find the calendar event whose time overlaps the recording, and identify the customer from the event title and attendee domains using Customers/_aliases.md. Append a dated entry to Customers/<Customer>.md with: meeting title, attendees, 3-5 line summary, decisions, and next steps as `- [ ] owner: task (due date)` checkboxes. Link back to the source file. Move processed files to Meetings/Processed. If you can't match a customer, leave the file in Inbox and list it for me.

2. Check the result against the original summary (see Verification). Adjust the prompt until two or three meetings come out right.
3. Save the prompt as a Hermes skill or a cron job that runs at the end of each workday.
4. Add a morning cron:

   > List every unchecked next step across Customers/*.md, grouped by customer, oldest due date first, plus anything due today.

## Human Gates

- Review extracted next steps for the first two weeks. Summaries sometimes turn "we should look at" into a commitment.
- Hermes doesn't email or message customers from this workflow.
- Recordings and transcripts can include other people's information. Keep the folder private and check your organization's recording policy.

## Verification

- Each processed meeting appears once, under the right customer, with a link to its source file.
- Next steps in the customer note match the Plaud summary. Nothing invented, nothing dropped.
- Unmatched files stay in Inbox and appear in Hermes's report instead of being guessed.

## Common Pitfalls

- **Name drift.** "Acme", "ACME Corp", and `@acme.com` attendees need to resolve to one note. Keep `_aliases.md` current.
- **Back-to-back meetings.** Match on the event whose time overlaps the recording most, not just the nearest start time.
- **Internal meetings.** Add a rule to skip or route meetings with only your own domain.
- **Duplicate runs.** Moving processed files out of Inbox is what prevents double entries. Don't skip it.

## Follow-up

_None yet._
