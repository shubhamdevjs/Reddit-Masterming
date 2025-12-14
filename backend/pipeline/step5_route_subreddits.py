import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer


def read_json(p: Path) -> Dict[str, Any]:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: Dict[str, Any]) -> None:
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _norm_text(s: str) -> str:
    return " ".join((s or "").split()).strip()


def build_subreddit_docs(subreddits: List[str]) -> List[str]:
    docs = []
    for sr in subreddits:
        sr_clean = _norm_text(sr)
        docs.append(f"subreddit: {sr_clean}")
    return docs


def build_title_docs_for_routing(
    title: str,
    company: Optional[Dict[str, str]] = None,
    persona: Optional[Dict[str, str]] = None,
    cluster_theme: Optional[str] = None,
) -> str:
    parts = [f"title: {_norm_text(title)}"]
    if cluster_theme:
        parts.append(f"cluster_theme: {_norm_text(cluster_theme)}")
    if company:
        parts.append(f"company: {_norm_text(company.get('name',''))}")
        parts.append(f"company_description: {_norm_text(company.get('description',''))}")
    if persona:
        parts.append(f"persona_username: {_norm_text(persona.get('persona_username',''))}")
        parts.append(f"persona_info: {_norm_text(persona.get('info',''))}")
    return "\n".join(parts)


def reassign_subreddits_cosine(
    request: Dict[str, Any],
    persona_titles_payload: Dict[str, Any],
    model_name: str = "all-MiniLM-L6-v2",
    top_k: int = 3,
    diversity_boost: bool = True,
) -> Dict[str, Any]:
    subreddits = request.get("subreddits", [])
    if not subreddits:
        raise ValueError("request['subreddits'] is empty")

    flattened = []
    for p_idx, p in enumerate(persona_titles_payload.get("personas", [])):
        for t_idx, t in enumerate(p.get("titles", [])):
            flattened.append((p_idx, t_idx, p, t))

    if not flattened:
        raise ValueError("No titles found in titles.json payload")

    emb_model = SentenceTransformer(model_name)

    subreddit_docs = build_subreddit_docs(subreddits)
    sr_emb = emb_model.encode(
        subreddit_docs,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    title_docs = []
    for _, _, persona_obj, t in flattened:
        title_docs.append(
            build_title_docs_for_routing(
                title=t.get("title", ""),
                company=request.get("company"),
                persona={
                    "persona_username": persona_obj.get("persona_username", ""),
                    "info": persona_obj.get("info", ""),
                },
                cluster_theme=t.get("cluster_theme") or None,
            )
        )

    title_emb = emb_model.encode(
        title_docs,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    sim = title_emb @ sr_emb.T

    used_counts = {sr: 0 for sr in subreddits}
    assigned = []

    for i in range(sim.shape[0]):
        scores = sim[i].copy()

        if diversity_boost:
            penalties = np.array([0.03 * used_counts[sr] for sr in subreddits], dtype=float)
            scores = scores - penalties

        top_idx = np.argsort(scores)[::-1][:top_k]
        candidates = [
            {"subreddit": subreddits[int(j)], "score": float(sim[i][int(j)])}
            for j in top_idx
        ]

        best_j = int(top_idx[0])
        best_sr = subreddits[best_j]
        used_counts[best_sr] += 1

        assigned.append((best_sr, candidates))

    out = {
        "meta": {
            "embedding_model": model_name,
            "top_k": top_k,
            "diversity_boost": diversity_boost,
            "num_subreddits": len(subreddits),
            "num_titles": len(flattened),
        },
        "personas": [],
    }

    for p in persona_titles_payload.get("personas", []):
        out["personas"].append({k: v for k, v in p.items() if k != "titles"} | {"titles": []})

    for idx, (p_idx, _t_idx, _p, t) in enumerate(flattened):
        best_sr, candidates = assigned[idx]
        new_t = dict(t)
        new_t["subreddit_assigned"] = best_sr
        new_t["subreddit_candidates"] = candidates
        out["personas"][p_idx]["titles"].append(new_t)

    return out


def main(company_dir: str):
    p = Path(company_dir)

    request = read_json(p / "request.json")
    titles_payload = read_json(p / "titles.json")

    routed = reassign_subreddits_cosine(
        request=request,
        persona_titles_payload=titles_payload,
        model_name="all-MiniLM-L6-v2",
        top_k=3,
        diversity_boost=True,
    )

    out_path = p / "titles_routed.json"
    write_json(out_path, routed)
    print(f"Wrote: {out_path}")

    # quick preview (first 2 personas, first 3 titles)
    for person in routed.get("personas", [])[:2]:
        print(f"\nPersona: {person.get('persona_username','')}")
        for t in person.get("titles", [])[:3]:
            top3 = [(c["subreddit"], round(c["score"], 3)) for c in t.get("subreddit_candidates", [])]
            print("-", t.get("title", ""))
            print("  assigned:", t.get("subreddit_assigned", ""), "| top3:", top3)


if __name__ == "__main__":
    main(sys.argv[1])
