# Preliminary Email Blacklist
# Generated: 2026-04-06 by Vera
# Source: Gmail promotions label, to:terminalman90@gmail.com, 2026-03-23 to 2026-04-06
# Method: is:unread + is:read searches, headers only, deduped manually
# Status: Preliminary - 14-day window only. Expand to 96 days (2026-01-01) next pass.

| # | Display Name | From Address | Alias? | Count |
|---|---|---|---|---|
| 1 | AMA Community | info@email.ama.ab.ca | | 1 |
| 2 | AIR MILES | no-reply@programnews.airmiles.ca | | 1 |
| 3 | Audible.ca | newsletters@audible.ca | Yes - see #2 | 6 |
| 4 | Audible.ca | noreply@mail.audible.ca | Yes - same sender | 3 |
| 5 | Amazon.ca | store-news@amazon.ca | | 6 |
| 6 | Claude Team | no-reply@email.claude.com | | 2 |
| 7 | Co-Active Coaching | service@coactive.com |  | 1+ |
| 8 | Edmonton Intl Airport | airportparking@flyeia.com | | 1 |
| 9 | Encor by EPCOR | encor@epcor.com | | 1 |
| 10 | Google Maps | noreply-local-guides@google.com |  | 1+ |
| 11 | Indeed | donotreply@match.indeed.com | Yes - also uses @indeed.com | 1 |
| 12 | Linked In | messages-noreply@linkedin.com |  | 1+ |
| 13 | Linked In | updates-noreply@linkedin.com |  | 1+ |
| 14 | Nate's Substack | natesnewsletter@substack.com | Yes - Substack alias pattern | 1 |
| 15 | PayPal | noreply@news.paypal.com | | 1 |
| 16 | Pocket Informant | support@pocketinformant.com | | 2 |
| 17 | Real Python | info@realpython.com |  | 1+ |
| 18 | Substack | canresist@substack.com |  | 1+ |
| 19 | Tangerine | forwardbanking@email.tangerine.ca | | 1 |
| 20 | TransUnion | transunion@em-tuci.transunion.com |  | 1+ |

## Summary
- 27 total messages over 14 days
- 12 unique senders, 13 unique addresses
- Audible confirmed multi-domain sender (newsletters@ and noreply@mail.)

## Notes
- Claude Team emails landing in promotions -- worth filtering to primary
- AIR MILES updating T&Cs June 2026 -- may want to keep temporarily
- Pocket Informant sending marketing to a registered user account
- Indeed using match.indeed.com subdomain -- may also send from @indeed.com

## Next Steps
- Expand window to 2026-01-01 (96 days) for fuller picture
- Consider gmail_promotions_bot (Ash cron) to maintain list automatically
- Decide: unsubscribe vs filter-to-label vs blacklist per sender
