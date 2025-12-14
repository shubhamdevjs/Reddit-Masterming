import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List


def read_json(p: Path) -> Any:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: Any) -> None:
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main(company_dir: str):
    p = Path(company_dir)

    # This is your existing flat output from step12
    flat = read_json(p / "reddit_output.json")

    posts: List[Dict[str, Any]] = flat.get("posts", [])
    comments: List[Dict[str, Any]] = flat.get("comments", [])
    meta: Dict[str, Any] = flat.get("meta", {})

    # Group comments by post_id
    by_post: Dict[str, List[Dict[str, Any]]] = {}
    for c in comments:
        pid = c.get("post_id", "")
        if pid not in by_post:
            by_post[pid] = []
        by_post[pid].append(
            {
                "comment_id": c.get("comment_id", ""),
                "post_id": c.get("post_id", ""),
                "parent_comment_id": c.get("parent_comment_id", ""),
                "comment_text": c.get("comment_text", ""),
                "username": c.get("username", ""),
                "timestamp": c.get("timestamp", ""),
                "Column 7": c.get("Column 7", ""),
            }
        )

    # Ensure stable ordering: timestamp, then comment_id
    for pid in by_post:
        by_post[pid].sort(key=lambda x: (x.get("timestamp", ""), x.get("comment_id", "")))

    # Attach comments to each post
    nested_posts: List[Dict[str, Any]] = []
    for post in posts:
        pid = post.get("post_id", "")
        new_post = dict(post)
        new_post["comments"] = by_post.get(pid, [])
        nested_posts.append(new_post)

    out = {
        "posts": nested_posts,
        "meta": {
            **meta,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "counts": {
                "posts": int(len(nested_posts)),
                "comments": int(len(comments)),
            },
        },
    }

    out_path = p / "reddit_output_nested.json"
    write_json(out_path, out)


if __name__ == "__main__":
    main(sys.argv[1])
