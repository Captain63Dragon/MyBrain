"""
scoring_service.py — Policy-driven todo scorer.
User-facing infrastructure. Not persona-owned.

score_todo(todo, policy, now) → (score, nudge)

Policy weights read from (:ScoringPolicy) node in Neo4j.
Caller decides what to score — no filtering here.

Updated: 2026-04-20
"""

from datetime import date, datetime


# ── Policy reader ─────────────────────────────────────────────────────────────

def get_scoring_policy(session, policy_id: str = 'todo-rank-v1') -> dict | None:
    """
    Read scoring policy weights from Neo4j.
    Returns plain dict or None if not found.
    """
    result = session.run(
        "MATCH (p:ScoringPolicy {`policy_id`: $policy_id}) RETURN p",
        policy_id=policy_id
    )
    record = result.single()
    if not record:
        return None
    return dict(record['p'])


# ── Scorer ────────────────────────────────────────────────────────────────────

def score_todo(todo: dict, policy: dict, now: datetime) -> tuple[float, bool]:
    """
    Score a single todo against a policy.

    Args:
        todo:   dict with keys: priority, created, due, friction
        policy: dict from (:ScoringPolicy) node
        now:    datetime to compute age against

    Returns:
        (score, nudge)
        score — float, higher = more urgent
        nudge — True if friction item has aged past friction_nudge_days
    """
    priority = (todo.get('priority') or 'low').lower()

    # Age in days
    created = todo.get('created')
    if created:
        if hasattr(created, 'to_native'):
            created = created.to_native()
        if isinstance(created, datetime):
            age_days = (now - created).days
        else:
            age_days = 0
    else:
        age_days = 0

    # ── Priority base ─────────────────────────────────────────────────────────
    base = {
        'high':   policy['weight_high'],
        'medium': policy['weight_medium'],
        'low':    policy['weight_low'],
    }.get(priority, policy['weight_low'])

    # ── Age component ─────────────────────────────────────────────────────────
    age_mult = {
        'high':   policy['age_mult_high'],
        'medium': policy['age_mult_medium'],
        'low':    policy['age_mult_low'],
    }.get(priority, policy['age_mult_low'])
    age_component = min(age_days * age_mult, policy['age_cap'])

    # ── Due component ─────────────────────────────────────────────────────────
    due_component = 0
    due_val = todo.get('due')
    if due_val:
        due_component += policy['bonus_due']
        # Resolve due to a date object
        if hasattr(due_val, 'to_native'):
            due_val = due_val.to_native()
        if isinstance(due_val, datetime):
            due_val = due_val.date()
        if isinstance(due_val, date) and due_val < now.date():
            due_component += policy['bonus_overdue']
    due_component = min(due_component, policy['due_cap'])

    # ── Friction component ────────────────────────────────────────────────────
    friction_component = 0
    nudge = False
    if todo.get('friction'):
        raw = (age_days * policy['friction_age_mult']) - policy['friction_suppressor']
        friction_component = max(
            min(raw, policy['friction_age_cap']),
            policy['friction_floor']
        )
        nudge = age_days >= policy['friction_nudge_days']

    score = base + age_component + due_component + friction_component
    return round(score, 1), nudge


# ── Batch scorer ──────────────────────────────────────────────────────────────

def score_and_rank(todos: list[dict], policy: dict, now: datetime, limit: int = 100) -> list[dict]:
    """
    Score and rank a list of todos. Returns top `limit` by score DESC.
    Adds 'score' and 'nudge' keys to each todo dict.
    """
    scored = []
    for todo in todos:
        s, nudge = score_todo(todo, policy, now)
        todo = dict(todo)
        todo['score'] = s
        todo['nudge'] = nudge
        scored.append(todo)

    scored.sort(key=lambda t: t['score'], reverse=True)
    return scored[:limit]