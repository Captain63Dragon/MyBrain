FROM:      Tim Rosborough <tim@zaudi.com>
DATE:      2026-04-17T21:11:15-06:00
SUBJECT:   [Note]Microservices - garden philosophy
SOURCE:    0fb6ce97b9caae9ba83a6aa403afef94.eml
---
So microservices. In the "garden", useful for the garden or rent on the
garden?

*Key distinction: Who owns the pipe?*

*Useful FOR the garden (equity-building):*

   - *Self-hosted microservices* (Neo4j, Flask, your future Public Server)
   - YOU run them, no external dependency
   - *One-time enrichment* (geocode an address via free API) - data enters
   garden, dependency ends
   - *Open protocols* (IMAP, CalDAV) - standards you can swap providers for
   - *Local MCP servers* - run on your machine, talk to your data

*Rent ON the garden (extractive):*

   - *Per-use API costs* (cloud OCR at $0.01/page) - scales with your
   usage, never ends
   - *Proprietary lock-in* (service-specific data formats) - can't leave
   without losing functionality
   - *Freemium traps* (free until you need it) - garden grows, then paywall
   hits
   - *Rate-limited dependencies* - works today, breaks when you scale

*MyBrain's current architecture = all equity:*

   - Neo4j: self-hosted (Docker on your machine)
   - Flask: self-hosted (Docker on your machine)
   - MCP: local bridges to local services
   - No external API dependencies

*Test for microservices:*

   - "If this service disappeared tomorrow, do I lose access to my data?" →
   NO = equity
   - "Does my usage accumulate costs?" → NO = equity
   - "Can I swap this for an alternative?" → YES = equity
