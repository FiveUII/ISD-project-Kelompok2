---
status: complete
phase: 04-fines-notifications
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md]
started: 2026-06-09T13:30:00Z
updated: 2026-06-09T14:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Fine auto-calculation on overdue return
expected: Manually set a loan's due_date to yesterday, then return it via the Return button on /librarian/loans. The return succeeds. Navigating to /librarian/fines shows a new fine row for that loan with a non-zero amount and status "unpaid".
result: pass

### 2. Librarian Fines Dashboard
expected: /librarian/fines (reachable via Fines link in NavBar) shows a table with columns for student name, book title, days overdue, amount, status badge, Pay button, and Waive button. Fines with status paid or waived have their Pay/Waive buttons disabled.
result: pass

### 3. Pay a fine
expected: Click Pay on an unpaid fine row. A ConfirmDialog appears asking to confirm. After confirming, the fine's status badge changes to "paid" and the Pay/Waive buttons become disabled.
result: pass

### 4. Waive a fine
expected: Click Waive on an unpaid fine row. A dialog opens with a textarea for the waiver reason. Entering a reason and submitting changes the fine's status badge to "waived" and disables Pay/Waive buttons. Submitting with an empty reason should be blocked (submit button disabled or error shown).
result: pass

### 5. APScheduler startup and notification logs
expected: After running `docker compose up` (fresh or restarted), the backend container logs show the APScheduler starting and the notification job firing once at startup. Log lines should mention reminder_count and overdue_count (e.g., "Notification job complete: 0 reminders, 0 overdue").
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
