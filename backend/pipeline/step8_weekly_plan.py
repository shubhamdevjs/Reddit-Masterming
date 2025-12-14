import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

A = 3  # max posts per persona per week
B = 2  # max posts per subreddit per week
C = 1  # max posts per persona-subreddit pair per week

SIM_THRESHOLD_SAME_SUBREDDIT = 0.82


def read_json(p: Path) -> Dict[str, Any]:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: Any) -> None:
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def flatten_posts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    posts = []
    for person in payload.get("personas", []):
        pu = person.get("persona_username", "")
        for t in person.get("titles", []):
            posts.append(
                {
                    "persona_username": pu,
                    "subreddit": t.get("subreddit_assigned") or t.get("subreddit"),
                    "title": t.get("title"),
                    "cluster_id": t.get("cluster_id"),
                    "keyword_ids": t.get("keyword_ids", []),
                    "index_in_persona": t.get("index_in_persona"),
                    "body": t.get("body"),
                    "raw": t,
                }
            )
    return posts


def cosine_sim(u: np.ndarray, v: np.ndarray) -> float:
    return float(np.dot(u, v))


def build_embeddings_matrix(posts: List[Dict[str, Any]], model_name: str = "all-MiniLM-L6-v2") -> np.ndarray:
    model = SentenceTransformer(model_name)
    texts = [
        f"{p.get('title','')} | {p.get('subreddit','')} | cluster {p.get('cluster_id','')}"
        for p in posts
    ]
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=64)
    return np.asarray(emb, dtype=float)


def violates_similarity(
    cand_idx: int,
    chosen_indices: List[int],
    posts: List[Dict[str, Any]],
    emb: np.ndarray,
) -> bool:
    cand_sr = posts[cand_idx]["subreddit"]
    for j in chosen_indices:
        if posts[j]["subreddit"] == cand_sr:
            if cosine_sim(emb[cand_idx], emb[j]) >= SIM_THRESHOLD_SAME_SUBREDDIT:
                return True
    return False


def schedule_weeks(
    posts: List[Dict[str, Any]],
    emb: np.ndarray,
    target_posts_per_week: int,
) -> List[Dict[str, Any]]:
    remaining_indices = list(range(len(posts)))

    weeks: List[Dict[str, Any]] = []
    week_num = 1

    while remaining_indices:
        chosen_idx: List[int] = []

        persona_count = defaultdict(int)
        subreddit_count = defaultdict(int)
        pair_count = defaultdict(int)
        cluster_count = defaultdict(int)

        def can_take(i: int, persona_cap: int, subreddit_cap: int) -> bool:
            pu = posts[i]["persona_username"]
            sr = posts[i]["subreddit"]
            pair = (pu, sr)

            if persona_count[pu] >= persona_cap:
                return False
            if subreddit_count[sr] >= subreddit_cap:
                return False
            if pair_count[pair] >= C:
                return False
            if violates_similarity(i, chosen_idx, posts, emb):
                return False
            return True

        def score_of(i: int, mode: str = "strict") -> float:
            pu = posts[i]["persona_username"]
            sr = posts[i]["subreddit"]
            cid = posts[i].get("cluster_id")
            idxp = posts[i].get("index_in_persona")

            if mode == "strict":
                score = 0.0
                score += 2.0 if subreddit_count[sr] == 0 else -0.2
                score += 1.5 if persona_count[pu] == 0 else -0.1
                if cid is not None:
                    score += 1.0 if cluster_count[cid] == 0 else -0.3
                if isinstance(idxp, int):
                    score += 0.15 * (1.0 / max(1, idxp))
                return score

            score = 0.0
            score += 1.0 if subreddit_count[sr] == 0 else -0.1
            score += 0.8 if persona_count[pu] == 0 else -0.05
            if cid is not None:
                score += 0.6 if cluster_count[cid] == 0 else -0.2
            return score

        def pick_one(persona_cap: int, subreddit_cap: int, mode: str) -> int | None:
            best_idx = None
            best_score = -1e9

            for pos, cand_i in enumerate(remaining_indices):
                if not can_take(cand_i, persona_cap, subreddit_cap):
                    continue

                sc = score_of(cand_i, mode=mode)
                if sc > best_score:
                    best_score = sc
                    best_idx = pos

            if best_idx is None:
                return None

            chosen_global_i = remaining_indices.pop(best_idx)

            pu = posts[chosen_global_i]["persona_username"]
            sr = posts[chosen_global_i]["subreddit"]
            pair = (pu, sr)
            cid = posts[chosen_global_i].get("cluster_id")

            chosen_idx.append(chosen_global_i)
            persona_count[pu] += 1
            subreddit_count[sr] += 1
            pair_count[pair] += 1
            if cid is not None:
                cluster_count[cid] += 1

            return chosen_global_i

        while remaining_indices and len(chosen_idx) < target_posts_per_week:
            if pick_one(A, B, mode="strict") is None:
                break

        if remaining_indices and len(chosen_idx) < target_posts_per_week:
            relax_A = A + 1
            relax_B = B + 1
            while remaining_indices and len(chosen_idx) < target_posts_per_week:
                if pick_one(relax_A, relax_B, mode="relaxed") is None:
                    break

        chosen_posts = [posts[i] for i in chosen_idx]

        weeks.append(
            {
                "week": week_num,
                "posts": chosen_posts,
                "counts": {
                    "num_posts": len(chosen_posts),
                    "unique_personas": len({p["persona_username"] for p in chosen_posts}),
                    "unique_subreddits": len({p["subreddit"] for p in chosen_posts}),
                    "unique_clusters": len({p.get("cluster_id") for p in chosen_posts}),
                },
            }
        )
        week_num += 1

        if len(chosen_posts) == 0:
            break

    return weeks


def strip_raw_fields(weekly_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []
    for w in weekly_plan:
        cleaned_posts = []
        for p in w.get("posts", []):
            cleaned_posts.append(
                {
                    "persona_username": p.get("persona_username"),
                    "subreddit": p.get("subreddit"),
                    "title": p.get("title"),
                    "body": p.get("body"),
                    "cluster_id": p.get("cluster_id"),
                    "keyword_ids": p.get("keyword_ids", []),
                    "index_in_persona": p.get("index_in_persona"),
                }
            )
        cleaned.append({"week": w.get("week"), "counts": w.get("counts"), "posts": cleaned_posts})
    return cleaned


def main(company_dir: str):
    p = Path(company_dir)

    posts_payload = read_json(p / "posts_with_bodies.json")
    capacity = read_json(p / "capacity.json")

    target = int(capacity["final"]["feasible_posts_per_week"])

    posts = flatten_posts(posts_payload)
    if not posts:
        raise ValueError("No posts found in posts_with_bodies.json")

    emb = build_embeddings_matrix(posts)

    weekly_plan = schedule_weeks(posts, emb, target_posts_per_week=target)
    weekly_plan = strip_raw_fields(weekly_plan)

    out_path = p / "weekly_plan.json"
    write_json(out_path, weekly_plan)


if __name__ == "__main__":
    main(sys.argv[1])
