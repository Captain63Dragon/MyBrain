# Pin Disambiguation Guide
**Date:** 2026-03-24 (from March 26 rollup pin)  
**Status:** Philosophy / Design Document  
**Priority:** HIGH (original rollup designation)  
**Source:** 2026_0326-pin_rollup-various.md  

---

## The Problem

The term "pin" is overloaded across **5+ contexts** in OurBrain system. This creates confusion about which "pin" to use when.

## The Five Contexts

### 1. In-Context Pin
**Usage:** "Pin that thought" (conversational marker)  
**Purpose:** Flag idea mid-conversation for later extraction  
**Output:** None - conversational only  
**Example:** User says "pin that" during discussion

### 2. Cork Board Pin
**Usage:** Save to chat/document (persistence)  
**Purpose:** Preserve information for later reference  
**Output:** Saved in conversation or document  
**Example:** "Pin this code snippet for later"

### 3. Todo Pin
**Usage:** Actionable item  
**Purpose:** Create a task to be completed  
**Output:** Todo node in graph  
**Example:** "Pin: Call dentist tomorrow"

### 4. Pip's Literal Pin (Canonical)
**Usage:** YAML file creation (Pip's job)  
**Purpose:** Formal pin file output from Pip persona  
**Output:** .yaml file in E:\_Processing\incoming\vera_pins\  
**Format:** Structured YAML with metadata, intended-for, todo specs  
**Example:** `2026_0318-pin-vera_bot_library_design.yaml`

### 5. Calendar Pin / Reminder
**Usage:** Temporal trigger / future reminder  
**Purpose:** Schedule something for specific date/time  
**Output:** Calendar event in Pip's calendar (parking space)  
**Example:** Fixed event at 2020-10-10 for sorting

## Decision Tree

**User phrase indicates:**
- "Pin this thought / idea" → **In-context** (conversational)
- "Save this / keep this" → **Cork board** (persistence)
- "Remind me to / I need to" → **Todo** OR **Calendar** (depending on time specificity)
- Pip creating output → **Literal pin** (YAML file)
- "At 3pm remind me" → **Calendar pin** (temporal)

## Context Clues

| Phrase Pattern | Pin Type |
|---|---|
| "Pin that..." (mid-conversation) | In-context |
| "Save this code/link/info" | Cork board |
| "I need to..." (no time) | Todo |
| "Remind me tomorrow at..." | Calendar |
| Pip output directive | Literal YAML |

## Policy Dependencies

This guide requires:
- **Policy Node Architecture** (to formalize decision rules)
- **Pip Canonical Pin Format** (to document literal pin structure)
- **Vocabulary Term Variants** (to create distinct Term nodes for each context)

## Implementation Path

1. ~~Document the five contexts~~ ✓ (this document)
2. Create Policy nodes for each pin type usage
3. Document Pip's canonical YAML format
4. Create Term node variants with SYNONYM_OF relationships
5. Build decision tree tool/prompt for personas
6. Test disambiguation in practice

## Related Work

- **Literal pin format:** See `todo-document-pip-format` (when created)
- **Policy architecture:** See `todo-policy-node-architecture` (when created)
- **Term variants:** See `todo-create-term-variants` (blocked by this guide)

---

**Notes:**
- Original rollup designated this as HIGH priority
- Resolves systematic ambiguity in OurBrain language
- Foundation for clearer persona communication
- Discovered/documented March 24, 2026
