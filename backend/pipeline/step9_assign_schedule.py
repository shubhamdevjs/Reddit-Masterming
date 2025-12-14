import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib


def read_json(p: Path):
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _stable_hash_int(s: str) -> int:
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:12], 16)


def infer_intent_from_text(title: str, body: str | None = None) -> str:
    t = (title or "").lower()
    b = (body or "").lower() if body else ""
    text = t + " " + b
    if any(x in text for x in [" vs ", " versus ", "compare", "comparison"]):
        return "compare"
    if any(x in text for x in ["alternative", "alternatives"]):
        return "alternatives"
    if any(x in text for x in ["best", "recommend", "recommendation"]):
        return "recommendation"
    if any(x in text for x in ["how to", "workflow", "automate", "automation", "faster"]):
        return "workflow"
    if "?" in (title or ""):
        return "question"
    return "general"


def subreddit_vibe_score(subreddit: str) -> str:
    s = (subreddit or "").lower()
    if any(k in s for k in ["powerpoint", "slides", "presentation", "consult", "startup", "productivity", "design"]):
        return "work"
    if any(k in s for k in ["ai", "claude", "ml", "gpt", "llm", "tech"]):
        return "tech"
    return "general"


def too_close(dt: datetime, others: list[datetime], min_gap_hours: int) -> bool:
    for o in others:
        if abs((dt - o).total_seconds()) < min_gap_hours * 3600:
            return True
    return False


def pick_time_in_window(
    base_date: datetime,
    persona: str,
    subreddit: str,
    title: str,
    window: tuple[int, int],
    salt: str,
) -> datetime:
    start_h, end_h = window
    window_minutes = max(1, (end_h - start_h) * 60)
    seed = f"{persona}|{subreddit}|{title}|{salt}"
    h = _stable_hash_int(seed)
    offset = h % window_minutes
    hour = start_h + (offset // 60)
    minute = offset % 60
    return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def derive_week_params(posts: list[dict]) -> dict:
    personas = [p.get("persona_username", "") for p in posts if p.get("persona_username")]
    subs = [p.get("subreddit", "") for p in posts if p.get("subreddit")]
    intents = [infer_intent_from_text(p.get("title", ""), p.get("body")) for p in posts]
    vibes = [subreddit_vibe_score(p.get("subreddit", "")) for p in posts]

    uniq_personas = max(1, len(set(personas)))
    uniq_subs = max(1, len(set(subs)))
    n = max(1, len(posts))

    diversity = (uniq_personas * uniq_subs) ** 0.5

    min_gap_persona_hours = int(round(4 + (8 / max(1.0, diversity))))
    min_gap_sub_hours = int(round(3 + (6 / max(1.0, uniq_subs / 2))))

    channels = max(1.0, min(uniq_personas, 5) * 0.7 + min(uniq_subs, 10) * 0.3)
    max_per_day = max(1, int(round(min(5, 1 + channels / 3))))

    work_ratio = sum(1 for v in vibes if v == "work") / n
    tech_ratio = sum(1 for v in vibes if v == "tech") / n
    question_ratio = sum(1 for i in intents if i in ["question", "workflow", "recommendation"]) / n

    return {
        "uniq_personas": uniq_personas,
        "uniq_subs": uniq_subs,
        "min_gap_persona_hours": min_gap_persona_hours,
        "min_gap_subreddit_hours": min_gap_sub_hours,
        "max_per_day": max_per_day,
        "work_ratio": work_ratio,
        "tech_ratio": tech_ratio,
        "question_ratio": question_ratio,
    }


def derive_time_windows_for_day(weekday: int, post_vibe: str, post_intent: str, week_params: dict) -> list[tuple[int, int]]:
    is_weekend = weekday >= 5

    work_bias = week_params["work_ratio"]
    tech_bias = week_params["tech_ratio"]
    q_bias = week_params["question_ratio"]

    late = 0.45
    if post_vibe == "tech":
        late += 0.15 * (0.6 + tech_bias)
    if post_vibe == "work":
        late -= 0.18 * (0.6 + work_bias)
    if post_intent in ["workflow", "compare"]:
        late += 0.08
    if post_intent in ["question", "recommendation"]:
        late -= 0.05 * (0.7 + q_bias)
    if is_weekend:
        late -= 0.10

    late = max(0.05, min(0.95, late))

    base_center = 12 + int(round(late * 10))
    if is_weekend:
        base_center -= 2

    diversity = (week_params["uniq_personas"] * week_params["uniq_subs"]) ** 0.5
    width = int(round(2 + (3 / max(1.0, diversity))))

    w1 = (max(8, base_center - width), min(23, base_center))
    w2 = (max(9, base_center), min(24, base_center + width + 1))

    windows = [w1, w2]
    if week_params["max_per_day"] >= 3:
        early_center = max(9, base_center - (width + 3))
        windows.insert(0, (max(8, early_center - 1), min(14, early_center + 2)))

    clean = []
    for a, b in windows:
        if b - a >= 1:
            clean.append((a, b))
    return clean


def _day_targets(n: int, week_seed: str, max_per_day: int) -> list[int]:
    targets = [0] * 7
    if n <= 0:
        return targets

    for i in range(n):
        base = int((i * 7) / n)
        j = (_stable_hash_int(f"{week_seed}|jitter|{i}") % 3) - 1
        d = (base + j) % 7

        stride = 1 + (_stable_hash_int(f"{week_seed}|stride|{i}") % 3)
        for _ in range(7):
            if targets[d] < max_per_day:
                targets[d] += 1
                break
            d = (d + stride) % 7
    return targets


def schedule_week_posts_rolling(posts: list[dict], week_start: datetime) -> list[dict]:
    n = len(posts)
    if n == 0:
        return []

    week_params = derive_week_params(posts)

    def sort_key(p):
        intent = infer_intent_from_text(p.get("title", ""), p.get("body"))
        order = {"question": 0, "recommendation": 1, "workflow": 2, "general": 3, "alternatives": 4, "compare": 5}
        return order.get(intent, 3)

    posts_sorted = sorted(posts, key=sort_key)

    days = [(week_start + timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0) for d in range(7)]

    week_seed = f"{week_start.date().isoformat()}|n={n}|p={week_params['uniq_personas']}|s={week_params['uniq_subs']}"
    day_capacity = _day_targets(n, week_seed, max_per_day=week_params["max_per_day"])

    persona_times = defaultdict(list)
    subreddit_times_by_day = defaultdict(list)
    day_load = [0] * 7
    scheduled = []

    def consecutive_penalty(d: int) -> float:
        left = day_load[d - 1] if d - 1 >= 0 else 0
        right = day_load[d + 1] if d + 1 <= 6 else 0
        return (1.0 if left > 0 else 0.0) + (0.7 if right > 0 else 0.0)

    base_order = list(range(7))
    base_order.sort(key=lambda d: (_stable_hash_int(f"{week_seed}|order|{d}") % 1000, d))

    for post in posts_sorted:
        persona = post.get("persona_username", "")
        subreddit = post.get("subreddit", "")
        title = post.get("title", "")
        body = post.get("body")

        intent = infer_intent_from_text(title, body)
        vibe = subreddit_vibe_score(subreddit)

        def day_score(d: int) -> float:
            score = 0.0

            if day_load[d] < day_capacity[d]:
                score += 3.0
            else:
                score -= 4.0

            score -= consecutive_penalty(d)

            if len(subreddit_times_by_day[(d, subreddit)]) == 0:
                score += 1.4
            else:
                score -= 0.6

            same_day_persona = len([t for t in persona_times[persona] if t.date() == days[d].date()])
            if same_day_persona == 0:
                score += 0.9
            else:
                score -= 0.9 * same_day_persona

            if intent in ["question", "workflow", "recommendation"]:
                score += (6 - d) * 0.02

            score += (_stable_hash_int(f"{persona}|{subreddit}|{title}|day{d}") % 100) / 10000.0
            return score

        day_order = sorted(base_order, key=day_score, reverse=True)

        placed = False
        for d in day_order:
            base_date = days[d]
            weekday = base_date.weekday()

            windows = derive_time_windows_for_day(
                weekday=weekday,
                post_vibe=vibe,
                post_intent=intent,
                week_params=week_params,
            )

            attempts = windows + windows

            for w_idx, win in enumerate(attempts):
                candidate_dt = pick_time_in_window(
                    base_date, persona, subreddit, title, win, salt=f"{week_seed}|{d}|{w_idx}"
                )

                if too_close(candidate_dt, persona_times[persona], week_params["min_gap_persona_hours"]):
                    continue
                if too_close(candidate_dt, subreddit_times_by_day[(d, subreddit)], week_params["min_gap_subreddit_hours"]):
                    continue

                persona_times[persona].append(candidate_dt)
                subreddit_times_by_day[(d, subreddit)].append(candidate_dt)
                day_load[d] += 1

                scheduled.append({**post, "scheduled_at": candidate_dt.isoformat()})
                placed = True
                break

            if placed:
                break

        if not placed:
            remaining = [(day_capacity[d] - day_load[d], d) for d in range(7)]
            remaining.sort(reverse=True)
            d = remaining[0][1] if remaining[0][0] > 0 else int(min(range(7), key=lambda x: day_load[x]))

            base_date = days[d]
            weekday = base_date.weekday()

            windows = derive_time_windows_for_day(
                weekday=weekday,
                post_vibe=vibe,
                post_intent=intent,
                week_params=week_params,
            )

            candidate_dt = pick_time_in_window(
                base_date, persona, subreddit, title, windows[0], salt=f"{week_seed}|fallback"
            )

            for _ in range(24):
                if (
                    not too_close(candidate_dt, persona_times[persona], week_params["min_gap_persona_hours"])
                    and not too_close(candidate_dt, subreddit_times_by_day[(d, subreddit)], week_params["min_gap_subreddit_hours"])
                ):
                    break
                candidate_dt += timedelta(minutes=45)

            persona_times[persona].append(candidate_dt)
            subreddit_times_by_day[(d, subreddit)].append(candidate_dt)
            day_load[d] += 1
            scheduled.append({**post, "scheduled_at": candidate_dt.isoformat()})

    scheduled.sort(key=lambda x: x["scheduled_at"])
    return scheduled


def assign_schedule_rolling(weekly_plan: list[dict], start_dt: datetime | None = None) -> list[dict]:
    start_dt = (start_dt or datetime.now()).replace(second=0, microsecond=0)

    scheduled = []
    for w in weekly_plan:
        week_index = int(w["week"]) - 1
        week_start = start_dt + timedelta(days=7 * week_index)

        scheduled_posts = schedule_week_posts_rolling(w.get("posts", []), week_start)

        scheduled.append(
            {
                "week": w["week"],
                "week_start": week_start.isoformat(),
                "week_end": (week_start + timedelta(days=6)).isoformat(),
                "posts": scheduled_posts,
            }
        )
    return scheduled


def main(company_dir: str, start_iso: str | None = None):
    p = Path(company_dir)
    weekly_plan = read_json(p / "weekly_plan.json")

    if start_iso:
        start_dt = datetime.fromisoformat(start_iso)
    else:
        start_dt = datetime.now().replace(second=0, microsecond=0)

    scheduled_plan = assign_schedule_rolling(weekly_plan, start_dt=start_dt)

    out_path = p / "scheduled_plan.json"
    write_json(out_path, scheduled_plan)


if __name__ == "__main__":
    company_dir_arg = sys.argv[1]
    start_iso_arg = sys.argv[2] if len(sys.argv) >= 3 else None
    main(company_dir_arg, start_iso=start_iso_arg)
