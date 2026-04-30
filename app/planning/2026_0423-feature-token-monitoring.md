# Token & Context Monitoring
**Feature Request & Design Document**  
Author: Iris | Date: 2026-04-23 | Status: Draft  
Owner: Rex | Linked: todo-1776952427454

---

## 1. Problem Statement

Every Anthropic API call re-transmits the full conversation context. As a session grows, input token cost compounds — not because individual exchanges are expensive, but because history accumulates silently. Without visibility into this growth, there is no basis for optimization decisions.

The original fuel consumption monitoring system was designed to track this. It stalled when Anthropic removed token count visibility from tool returns visible to Claude. That data was never gone — it was always present in the API response usage object. It simply stopped surfacing inside the conversation.

> The `/v1/messages/count_tokens` endpoint (introduced late 2024) and the `usage` object in every API response provide the ground truth. The gap was visibility, not availability.

---

## 2. How Context Scales

Each round trip to the Anthropic API carries:

| Component | Size | Notes |
|---|---|---|
| System prompt | Large, fixed | Project context + persona files + skill files. Loaded once, repeated every call. |
| Conversation history | Grows every turn | Full message history re-sent. The primary cost driver in long sessions. |
| Tool schemas | Medium, semi-fixed | Bot registry loaded on startup. Repeated on every call that uses tools. |
| Tool result JSON | Variable | MCP tool returns embedded in context. Fat results inflate fast. |
| Model response | Small–medium | Output tokens. Generally the smallest component. |

**The compounding formula:**
```
input_tokens(turn N) = system_prompt + Σ(all previous messages) + tool_schemas + tool_result(N)
```

By turn 20 of a heavy tool-use session, input_tokens is dominated by history re-transmission. The work of turn 20 may be 200 tokens. The overhead of carrying turns 1–19 may be 15,000.

> Design implication: restarting context when a discrete task completes is the primary lever for cost control. Session boundaries matter.

---

## 3. What Is Now Observable

### 3.1 API Response Usage Object

Every Anthropic API response includes:
```json
{
  "input_tokens": 1842,
  "output_tokens": 12,
  "cache_creation_input_tokens": 0,
  "cache_read_input_tokens": 0
}
```

- `input_tokens` — full context size at that call
- `output_tokens` — response size
- `cache_creation_input_tokens` — tokens written to prompt cache (one-time cost)
- `cache_read_input_tokens` — tokens served from cache (significantly cheaper)

The MCP bridge (`mcp_flask_bridge.py`) sits in the call path. It can capture this object for every tool call without any bot author involvement.

### 3.2 Count Tokens Endpoint

Pre-flight token estimation without consuming response credits:
```
POST https://api.anthropic.com/v1/messages/count_tokens
Response: { "input_tokens": N }
```

Useful for estimating cost before a heavy operation. Not required for post-call logging — the usage object provides actual counts after the fact.

> `count_tokens` returns an estimate. Actual billed tokens may differ slightly. System-added tokens are not billed.

---

## 4. Proposed Implementation

### 4.1 Bridge-Level Capture (Primary)

`mcp_flask_bridge.py` already wraps every tool call in `execute_tool_by_name()`. Adding usage capture here requires no changes to individual bots.

On each tool call response from the Anthropic API:
- Extract usage object
- Log to `bot_calls.log` as a new field: `usage: {input, output, cache_read, cache_created}`
- Update BotFunction node counters (covered by `todo-1776952427454`)

> Same middleware location proposed for BotFunction call counters. One wrapper, two responsibilities.

### 4.2 Update iris.analytics.measure.tokens

The current bot estimates tokens from character count (~4 chars/token). With real usage data available from the bridge, this bot should:
- Accept real usage data when passed in (bridge-captured)
- Fall back to character estimation when not available (degraded/meta mode)
- Report both actual and estimated figures when both are present for calibration

### 4.3 Session Boundary Logging

Tag the first and last `bot_calls.log` entry of each session. This enables:
- Per-session token totals (sum `input_tokens` from first to last entry)
- Context growth rate (`input_tokens` delta per turn)
- Session cost comparison across persona types

> Session start is already implicit in the reason string pattern. A persona name + startup reason is sufficient to identify session boundaries without new infrastructure.

---

## 5. Why This Is Worth Monitoring

### 5.1 Extended Thinking Visibility

Extended thinking tokens accumulate as input history. Monitoring `input_tokens` growth rate reveals when extended thinking sessions are compounding context debt.

### 5.2 Flail Detection

Flail — a persona making multiple tool calls without clear direction — is expensive. Each call re-transmits the full context. A spike in per-turn `input_token` delta with low `output_tokens` is a flail signature.

Monitoring cost: flail costs extra tokens. The counter-argument is that monitoring enables better instruction quality and skill tuning, which reduces flail over time. Net positive.

### 5.3 Tool Result Size Awareness

Large MCP tool returns embed in context and persist for the remainder of the session. The `input_tokens` delta before and after a heavy tool call reveals its context footprint. This informs:
- Which bots should have `log_call: false`
- Which bot results should be summarized before returning
- Optimal `limit` parameters for retrieval bots

### 5.4 Cache Effectiveness

`cache_read_input_tokens` vs `cache_creation_input_tokens` reveals whether prompt caching is working. A healthy session sees `cache_read` growing after the first call as the system prompt stabilizes.

---

## 6. Session Discipline Recommendations

No infrastructure change required. Observable immediately.

- End sessions when a discrete task completes. Context does not carry value between unrelated tasks.
- Heavy tool-use sessions accumulate context fast. Shorter sessions, more focused scope.
- Design-only sessions have minimal token growth. Back-and-forth conversation is cheap relative to tool calls.
- Tool results that return large payloads should be consumed and summarized in the same turn. Do not let large results sit in context unused.

> Today's session: design work dominated. Tool calls were targeted. Context growth was modest despite session length. This is the right pattern.

---

## 7. Implementation Checklist

| Task | Owner | Linked Todo |
|---|---|---|
| Capture usage object in bridge middleware | Rex | todo-1776952427454 |
| Log usage fields to bot_calls.log | Rex | todo-1776952427454 |
| Update iris.analytics.measure.tokens for real data | Iris | New |
| Session boundary tagging in log | Rex | New |
| Iris analysis script v2 — token metrics | Iris | New |
| Add usage capture note to tool_use_guidelines | Iris | todo-1776950638956 |

---

*MyBrain-2026 Internal Document | Iris | 2026-04-23 | Draft — pending Rex implementation*
