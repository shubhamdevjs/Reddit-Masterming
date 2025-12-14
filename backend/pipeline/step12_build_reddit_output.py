import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd


POSTS_COLS = ["post_id", "subreddit", "title", "body", "author_username", "timestamp", "keyword_ids"]
COMMENTS_COLS = ["comment_id", "post_id", "parent_comment_id", "comment_text", "username", "timestamp", "Column 7"]


def read_json(p: Path) -> Any:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def enforce_cols(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]


def flatten_scheduled_posts(scheduled_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flat = []
    for w in scheduled_plan:
        for p in w.get("posts", []):
            flat.append(p)
    flat.sort(key=lambda x: x.get("scheduled_at", ""))
    return flat


def main(company_dir: str):
    p = Path(company_dir)

    scheduled_plan = read_json(p / "scheduled_plan.json")
    comments_with_text = read_json(p / "comments_with_text.json")

    # Build posts_rows
    posts_rows: List[Dict[str, Any]] = []
    flat_posts = flatten_scheduled_posts(scheduled_plan)

    pid = 1
    for post in flat_posts:
        kid = post.get("keyword_ids", [])
        if isinstance(kid, list):
            kid_val = ", ".join(kid)
        else:
            kid_val = kid or ""

        posts_rows.append(
            {
                "post_id": f"P{pid}",
                "subreddit": post.get("subreddit") or post.get("subreddit_assigned") or "",
                "title": post.get("title", "") or "",
                "body": post.get("body", "") or "",
                "author_username": post.get("persona_username", "") or "",
                "timestamp": post.get("timestamp") or post.get("scheduled_at") or "",
                "keyword_ids": kid_val,
            }
        )
        pid += 1

    # Build comments_rows (normalize)
    comments_rows: List[Dict[str, Any]] = []
    for c in comments_with_text:
        comments_rows.append(
            {
                "comment_id": c.get("comment_id", "") or "",
                "post_id": c.get("post_id", "") or "",
                "parent_comment_id": c.get("parent_comment_id", "") or "",
                "comment_text": c.get("comment_text", "") or "",
                "username": c.get("username", "") or "",
                "timestamp": c.get("timestamp", "") or "",
                "Column 7": c.get("Column 7", "") or "",
            }
        )

    posts_df = pd.DataFrame(posts_rows)
    comments_df = pd.DataFrame(comments_rows)

    posts_df = enforce_cols(posts_df, POSTS_COLS).fillna("")
    comments_df = enforce_cols(comments_df, COMMENTS_COLS).fillna("")

    payload = {
        "posts": posts_df.to_dict(orient="records"),
        "comments": comments_df.to_dict(orient="records"),
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "counts": {"posts": int(len(posts_df)), "comments": int(len(comments_df))},
            "schema": {"posts_cols": POSTS_COLS, "comments_cols": COMMENTS_COLS},
        },
    }

    out_path = p / "reddit_output.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
