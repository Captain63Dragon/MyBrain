# Feature Request: Bank Alert + Statement Reconciliation Pipeline
Created: 2026-04-22 by Vera
Todo: todo-1776873571843

## Problem
Scotia alerts every transaction including trivial ones (gum, groceries).
Alerts currently route to two addresses (Tim@zaudi.com and terminalman90@gmail.com) - mixed, noisy, unactionable at volume.
The purpose of an alert is to flag the unexpected. When everything fires, nothing is a signal.

## Sample Files
- Alert extract xlsx: C:\Users\termi\Dropbox\Saves\2026_0422-scotia-alerts-VeraReview_001.xlsx
- Source label: Gmail > VeraReview

## Goal
Two outputs from one pipeline:

1. **Anomaly Flag** - transactions in bank statement with no matching alert email
   (unknown activity: fraud, Monica's purchases, anything unexpected)

2. **Spending Context** - categorized summary on user's terms, not the bank's
   (where the money actually goes, filtered by what is important to the user)

## Inputs
- Bank statement CSV (downloaded manually, dropped to staging folder)
- Scotia alert emails from VeraReview Gmail label (already in mybrain pipe)

## Matching Logic
- Match alert emails to statement rows by: amount + date + approximate time window
- Matched → categorize, explain, summarize
- Statement row with no alert → FLAG as unknown activity
- Alert with no statement row → note as pending / not yet posted

## Design Constraints
- No bank API, no account access - statement CSV is ground truth
- Emails are context and early warning layer only
- User downloads statement, drops to staging folder - hands-off from there
- Output: summary report + flagged items only (not a full transaction log)

## Pre-requisites (user actions)
- Consolidate Scotia alert destination to a single email address
- Set up auto-forward: Tim@zaudi.com → mybrain@zaudi.com
  Filter: from @scotiabank.com OR @payments.interac.ca

## Broader Pattern
This same approach applies to any monitored inbox:
- Utilities
- Subscriptions
- Any service sending transactional emails
Automate the review, surface only what needs attention.
The inbox becomes an intake pipe, not a pile.

## Design Notes
(append future decisions here)
