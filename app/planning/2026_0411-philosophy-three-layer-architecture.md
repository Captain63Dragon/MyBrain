# Three-Layer Knowledge Architecture
**Date:** 2026-03-24 (from March 26 rollup pin)  
**Status:** Philosophy / Architecture Design  
**Source:** 2026_0326-pin_rollup-various.md  

---

## The Three Layers

System knowledge is organized in three layers, each answering a different question:

1. **Vocabulary** (WHAT we call things)
2. **Policy** (HOW we do things)
3. **Principles** (WHY we do them this way)

## Principles Defined

> "Guiding philosophy and directives that inform decision-making when rules are unclear. Not just definitions, not just instructions - principles point in a direction. They're the 'north star' that guides choices when navigating ambiguity."

## Examples Discovered

- "Ground truth goes in permanent storage" (data architecture principle)
- "Ore → Crucible → Nugget" (compression principle)
- "Memory of OurBrain" (persistence principle)
- "Temporary scratch space → permanent storage" (information flow principle)
- "Forward-only versioning" (corruption detection principle)
- "Atomic operations, composed at persona level" (bot library principle)

## Distinctions

### Principles vs Policies

- **Policy:** "Always provide clickable calendar links after event creation"
- **Principle:** "Make information immediately accessible to users in their context"

### Principles vs Terms

- **Term:** "Pin" - definition of what the word means
- **Principle:** "Pins are contextual dispatch" - philosophy of overloaded usage

## Architecture Implications

Need graph structure for Principles:
- `PrincipleCategory` nodes (like VocabularyCategory)
- `Principle` nodes with definitions
- Relationships: GUIDES, INFORMS, UNDERLIES
- Global vs persona-specific scope
- Links to Policies (Principle UNDERLIES Policy)
- Links to Terms (Principle INFORMS Term)

## Use Cases

When persona uncertain how to handle a situation:
1. Check Policies for explicit rules
2. If no policy exists, check Principles for guidance
3. Make decision aligned with Principles
4. Log decision as potential new Policy candidate

## Meta-Principle

**"The system needs Principles."**

This itself is a principle - the meta-principle that guided this discovery. Without principles, we have rules without understanding why.

## Value Proposition

- Personas can make aligned decisions even without explicit rules
- System design becomes teachable (principles > rote memorization)
- New policies can be validated against principles
- Principle violations signal design drift
- OurBrain learns not just what to do, but why

---

## Implementation Status

**Concept:** Documented  
**Graph Schema:** Not yet designed  
**Node Types:** Not yet created  
**Policy Nodes:** Also not yet created (see proposal-policy-node-architecture.md when created)

**Next Steps:**
1. Design Policy node architecture first (foundation layer)
2. Design Principle node architecture
3. Create relationship types
4. Implement graph structure
5. Populate with discovered principles
6. Build querying/navigation tools

---

**Notes:**
- Breakthrough discovery from March 24, 2026 session
- Third layer of knowledge architecture
- Completes the WHAT → HOW → WHY framework
