import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Tuple

from openai import OpenAI

MODEL_CANDIDATES = ["gpt-4o-mini", "gpt-4.1-mini"]
MAX_WORDS = 9


def read_json(p: Path) -> Any:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: Any) -> None:
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_json_loose(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(text[s : e + 1])
        raise


def cap_words(s: str, max_words: int = MAX_WORDS) -> str:
    words = [w for w in re.split(r"\s+", (s or "").strip()) if w]
    return " ".join(words[:max_words])


def call_with_fallback(client: OpenAI, prompt: str) -> str:
    last_err = None
    for m in MODEL_CANDIDATES:
        try:
            r = client.responses.create(
                model=m,
                input=prompt,
                max_output_tokens=160,
                temperature=0.4,
            )
            return r.output_text.strip()
        except Exception as e:
            last_err = e
    raise last_err


def flatten_scheduled_posts(scheduled_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flat = []
    for w in scheduled_plan:
        for p in w.get("posts", []):
            flat.append(p)
    flat.sort(key=lambda x: x.get("scheduled_at", ""))
    return flat


def build_post_comments_prompt(
    title: str,
    subreddit: str,
    company_name: str,
    company_description: str,
) -> str:
    sr = (subreddit or "").strip()
    sr = sr[2:] if sr.lower().startswith("r/") else sr

    return f"""
Generate authentic, organic Reddit comments for a post.

Context:
- Subreddit: r/{sr}
- Post Title: {title}
- Company: {company_name}
- Company Info: {company_description}

Requirements:
1. Generate exactly 3 distinct comments
2. Each comment MUST be <= {MAX_WORDS} words
3. Sound like real Reddit users, natural, casual
4. Subtly positive about {company_name}, no hard selling
5. Vary tone: curious question, brief experience, light endorsement
6. No emojis, no marketing language
7. Relevant to the post title

Return ONLY valid JSON:
{{"comments":["comment 1","comment 2","comment 3"]}}
""".strip()


def main(company_dir: str, max_posts: int | None = None):
    p = Path(company_dir)

    request = read_json(p / "request.json")
    scheduled_plan = read_json(p / "scheduled_plan.json")
    comment_plan = read_json(p / "comment_plan.json")

    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY is not set in environment")

    client = OpenAI()

    company_name = request["company"]["name"]
    company_description = request["company"]["description"]

    flat_posts = flatten_scheduled_posts(scheduled_plan)

    post_meta: Dict[str, Tuple[str, str]] = {}
    for i, post in enumerate(flat_posts, start=1):
        post_id = f"P{i}"
        post_meta[post_id] = (post.get("title", ""), post.get("subreddit", ""))

    rows_by_post = defaultdict(list)
    for r in comment_plan:
        rows_by_post[r["post_id"]].append(r)

    post_ids = sorted(set(r["post_id"] for r in comment_plan), key=lambda x: int(x[1:]))
    if max_posts is not None:
        post_ids = post_ids[:max_posts]

    comment_rows = []

    for post_id in post_ids:
        title, subreddit = post_meta.get(post_id, ("", ""))
        prompt = build_post_comments_prompt(title, subreddit, company_name, company_description)

        raw = call_with_fallback(client, prompt)
        obj = parse_json_loose(raw)
        comments = obj.get("comments", [])

        if not isinstance(comments, list) or len(comments) < 3:
            comments = ["Following this thread.", "Same question here.", "Thanks for sharing."]

        comments = [cap_words(c, MAX_WORDS) for c in comments[:3]]

        planned = rows_by_post[post_id]
        planned.sort(key=lambda x: x["timestamp"])

        for idx, row in enumerate(planned[:3]):
            out = {
                "comment_id": row["comment_id"],
                "post_id": row["post_id"],
                "parent_comment_id": row["parent_comment_id"],
                "comment_text": comments[idx],
                "username": row["username"],
                "timestamp": row["timestamp"],
            }
            comment_rows.append(out)

    out_path = p / "comments_with_text.json"
    write_json(out_path, comment_rows)


if __name__ == "__main__":
    company_dir_arg = sys.argv[1]
    max_posts_arg = int(sys.argv[2]) if len(sys.argv) >= 3 else None
    main(company_dir_arg, max_posts=max_posts_arg)
