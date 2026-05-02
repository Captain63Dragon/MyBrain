# Feature Spec: TOPS Food & Weight Tracker
<!-- Source: vera-queue/feature_request/2026_0428-feature_request-tops_food_weight_tracker_mobile_first_ai.txt -->
<!-- Filed: 2026-04-28 | Owners: Rex, Walter, Iris -->

## Summary
A mobile-first, AI-powered food and weight logging interface for TOPS compliance tracking.

## Pain Point
Manual logging has high friction; low compliance kills plateau-breaking progress.

## Problem
No low-friction entry point exists for daily food and weekly weigh-in data; Walter's spreadsheet has no input layer.

---

## Page 1: Food Log (Landing Page)

### Entry Flow - Category Wheel System
- **Wheel 1:** Category selector (Eat Out, Home Cook, Snack, etc.)
- **Wheel 2:** Unlocks on W1 - Venue / Source (populated from history)
- **Wheel 3:** Usual vs New
- **Wheel 4:** Item selector (known menu items or free entry)
- **Portion field:** Numeric free-entry (e.g. 90%, 150%) - no slider ceiling
- **Submit:** Returns AI-calculated nutrition panel

### Output Panel (per submission)
- Calories, Fiber, Protein, Sugar (portion-adjusted)
- Iris Meal Rating
- Remaining daily caloric balance

### Smart Defaults
- Auto-timestamp on every entry
- Time-of-day primes category defaults (morning → breakfast)
- "Same as last time" one-tap repeat
- Wheel 2 & 4 options populated from prior successful inputs

### Bottom Bar (Food Log page only)
- Star/strike streak display - daily entry hits and misses

---

## Page 2: Weigh-In (Sub-page)
- Weekly weight entry
- Trend chart over time
- Feeds Walter's rollup spreadsheet (pending)

---

## Page 3: Dashboard (Sub-page - utility link, not primary nav)
- Daily snapshot: calories remaining, today's Iris rating, streak status
- Weekly progress summary
- Accessible via link styled like new_todo.php utility link pattern

---

## Intelligence Layer
- Learns venue + item history from prior successful inputs
- Streak tracking drives compliance feedback loop

---

## Technical Notes
- Artifact-based (React/HTML inline, phone-first ~380px)
- Persistent storage via artifact key-value store; probably in database table
- AI nutrition lookup + Iris rating via Anthropic API in artifact
- Walter spreadsheet integration pending
- Download required in subsequent versions

## Owners
- **Rex** - build, architecture
- **Walter** - spreadsheet rollup layer
- **Iris** - form UI, AI rating layer

## Origin
Designed in Iris meta-mode session 2026-04-28. Wheel UI pattern originated from user 'bathtub thought' design session.
