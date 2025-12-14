import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

COMMENTS_PER_POST = 3


def read_json(p: Path):
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _stable_hash_int(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:12], 16)


def parse_iso(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str)


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def pick_commenters(all_usernames, op_username, n_unique=3, seed=""):
    """Pick N unique commenters (excluding OP) for a post's comments."""
    unique_users = list(dict.fromkeys(all_usernames))
    pool = [u for u in unique_users if u != op_username]
    if not pool:
        raise ValueError("No non-OP personas available for commenting")

    h = _stable_hash_int(seed)
    picked = []
    # Ensure we pick unique personas by using different offsets
    for i in range(min(n_unique, len(pool))):
        idx = (h + i * 7) % len(pool)
        u = pool[idx]
        if u not in picked:
            picked.append(u)
    
    # If we need more commenters than available, cycle through pool with different positions
    while len(picked) < n_unique:
        idx = (h + len(picked) * 11) % len(pool)
        picked.append(pool[idx])
    
    return picked


def schedule_comment_times(post_time: datetime, n_comments: int, seed: str):
    h = _stable_hash_int(seed)
    t = post_time + timedelta(minutes=12 + (h % 34))
    times = [t]
    for i in range(1, n_comments):
        h2 = _stable_hash_int(f"{seed}|{i}")
        t = t + timedelta(minutes=8 + (h2 % 28))
        times.append(t)
    return times


def flatten_scheduled_posts(scheduled_plan):
    flat = []
    for w in scheduled_plan:
        for p in w.get("posts", []):
            flat.append(p)
    flat.sort(key=lambda x: x["scheduled_at"])
    return flat


def main(company_dir: str):
    p = Path(company_dir)

    request = read_json(p / "request.json")
    scheduled_plan = read_json(p / "scheduled_plan.json")

    all_usernames = [x["persona_username"] for x in request.get("personas", [])]
    if len(all_usernames) < 2:
        raise ValueError("Need at least 2 personas total to create non-OP comments")

    flat_posts = flatten_scheduled_posts(scheduled_plan)

    comment_plan = []
    c_counter = 1

    for i, post in enumerate(flat_posts, start=1):
        post_id = f"P{i}"
        op = post.get("persona_username", "")
        title = post.get("title", "")
        subreddit = post.get("subreddit", "")
        post_time = parse_iso(post["scheduled_at"])

        seed = f"{post_id}|{op}|{subreddit}|{title}"
        commenters = pick_commenters(all_usernames, op, n_unique=3, seed=seed)
        times = schedule_comment_times(post_time, COMMENTS_PER_POST, seed=seed)

        c1 = f"C{c_counter}"; c_counter += 1
        c2 = f"C{c_counter}"; c_counter += 1
        c3 = f"C{c_counter}"; c_counter += 1

        # Decide structure based on hash: mix of standalone and threaded comments
        h = _stable_hash_int(seed + "|structure")
        structure_choice = h % 3

        if structure_choice == 0:
            # Pattern: standalone, reply to first, standalone
            comment_plan.append({
                "comment_id": c1,
                "post_id": post_id,
                "parent_comment_id": "",
                "username": commenters[0],
                "timestamp": fmt_dt(times[0]),
                "title": title,
                "subreddit": subreddit
            })
            comment_plan.append({
                "comment_id": c2,
                "post_id": post_id,
                "parent_comment_id": c1,
                "username": commenters[1],
                "timestamp": fmt_dt(times[1]),
                "title": title,
                "subreddit": subreddit
            })
            comment_plan.append({
                "comment_id": c3,
                "post_id": post_id,
                "parent_comment_id": "",
                "username": commenters[2],
                "timestamp": fmt_dt(times[2]),
                "title": title,
                "subreddit": subreddit
            })
        elif structure_choice == 1:
            # Pattern: all standalone comments
            comment_plan.append({
                "comment_id": c1,
                "post_id": post_id,
                "parent_comment_id": "",
                "username": commenters[0],
                "timestamp": fmt_dt(times[0]),
                "title": title,
                "subreddit": subreddit
            })
            comment_plan.append({
                "comment_id": c2,
                "post_id": post_id,
                "parent_comment_id": "",
                "username": commenters[1],
                "timestamp": fmt_dt(times[1]),
                "title": title,
                "subreddit": subreddit
            })
            comment_plan.append({
                "comment_id": c3,
                "post_id": post_id,
                "parent_comment_id": "",
                "username": commenters[2],
                "timestamp": fmt_dt(times[2]),
                "title": title,
                "subreddit": subreddit
            })
        else:
            # Pattern: standalone, standalone, reply to first
            comment_plan.append({
                "comment_id": c1,
                "post_id": post_id,
                "parent_comment_id": "",
                "username": commenters[0],
                "timestamp": fmt_dt(times[0]),
                "title": title,
                "subreddit": subreddit
            })
            comment_plan.append({
                "comment_id": c2,
                "post_id": post_id,
                "parent_comment_id": "",
                "username": commenters[1],
                "timestamp": fmt_dt(times[1]),
                "title": title,
                "subreddit": subreddit
            })
            comment_plan.append({
                "comment_id": c3,
                "post_id": post_id,
                "parent_comment_id": c1,
                "username": commenters[2],
                "timestamp": fmt_dt(times[2]),
                "title": title,
                "subreddit": subreddit
            })

    out_path = p / "comment_plan.json"
    write_json(out_path, comment_plan)


if __name__ == "__main__":
    main(sys.argv[1])
