---
status: testing
phase: 03-loans-circulation
source: [03-VERIFICATION.md]
started: 2026-06-09T11:48:00Z
updated: 2026-06-09T11:48:00Z
---

## Current Test

number: 1
name: Complete checkout → return → overdue detection cycle in running Docker Compose stack
expected: |
  Full circulation workflow works end-to-end: checkout creates active loan, return restores copy availability, overdue badge appears when due_date is past
awaiting: user response

## Tests

### 1. Checkout flow
expected: Librarian can check out an available copy to a student via the checkout modal (student search, select, confirm); copy status changes to On Loan
result: [pending]

### 2. Librarian Loans Dashboard
expected: /librarian/loans shows Active Loans tab with correct columns (student, book, copy, due date, status badge, Return button); Overdue tab filters by past-due date
result: [pending]

### 3. Return flow
expected: Clicking Return on an active loan shows ConfirmDialog; confirming removes the row and restores copy to Available on Book Detail page
result: [pending]

### 4. Student My Loans
expected: Student sees active loan card at /my-loans with book title and due date; no Overdue badge for current loans; empty state shown after return
result: [pending]

### 5. Overdue detection
expected: After manually setting due_date to yesterday, /my-loans shows red Overdue badge; /librarian/loans Overdue tab shows the loan
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
