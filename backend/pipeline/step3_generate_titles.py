import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from openai import OpenAI

MODEL_CANDIDATES = ["gpt-4.1-mini", "gpt-4o-mini", "gpt-4.1", "gpt-4o"]


def read_json(p: Path) -> Dict[str, Any]:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: Dict[str, Any]) -> None:
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_cluster_catalog(result: Dict[str, Any], max_clusters: int = 12) -> str:
    lines = []
    for c in (result.get("clusters") or [])[:max_clusters]:
        cid = c.get("cluster_id")
        theme = c.get("theme", "")
        ids = c.get("ids", [])
        kws = (c.get("keywords") or [])[:6]
        lines.append(
            f"- cluster_id: {cid} | theme: {theme} | keyword_ids: {ids} | keywords: {', '.join(kws)}"
        )
    return "\n".join(lines)


def cluster_hints(result: Dict[str, Any], max_clusters: int = 6) -> str:
    chunks = []
    for c in (result.get("clusters") or [])[:max_clusters]:
        theme = c.get("theme", "")
        kws = (c.get("keywords") or [])[:6]
        if theme and kws:
            chunks.append(f"- {theme}. {', '.join(kws)}")
        elif theme:
            chunks.append(f"- {theme}")
        elif kws:
            chunks.append(f"- {', '.join(kws)}")
    return "\n".join(chunks) if chunks else "- edge ai\n- on device llm\n- offline assistant\n- privacy\n- latency"


def parse_json_loose(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(text[s : e + 1])
        raise


def build_persona_titles_prompt(
    company: Dict[str, str],
    persona: Dict[str, str],
    subreddits: List[str],
    topic_hints: str,
    n_titles: int,
    cluster_catalog: str,
) -> str:
    subreddit_list = "\n".join([f"- {s}" for s in subreddits])

    return f"""
Generate Reddit post titles for ONE persona.

Persona:
username: {persona["persona_username"]}
info: {persona["info"]}

Company context:
name: {company["name"]}
description: {company["description"]}

Topic space hints:
{topic_hints}

Allowed subreddits (pick ONE per title from this list):
{subreddit_list}

Available clusters (pick ONE cluster per title from this list):
{cluster_catalog}

Task:
Create {n_titles} distinct, natural Reddit post titles that follow a realistic progression.
Do not output the story. Only output items.
Company should appear indirectly in some titles. Do not force it in all.

Rules for each title:
- 8 to 16 words
- Human, specific, not promotional
- No emojis
- Choose exactly one subreddit from Allowed subreddits
- Choose exactly one cluster_id from Available clusters
- The chosen cluster_id must match the intent of the title

Return JSON only:
{{
  "arc_label": "<short label>",
  "items": [
    {{
      "index_in_persona": 1,
      "subreddit": "r/...",
      "cluster_id": <int>,
      "keyword_ids": ["K1","K2"],
      "title": "<title>"
    }}
  ]
}}
""".strip()


def call_with_fallback(client: OpenAI, prompt: str) -> str:
    last_err = None
    for m in MODEL_CANDIDATES:
        try:
            r = client.responses.create(
                model=m,
                input=prompt,
                max_output_tokens=800,
            )
            return r.output_text.strip()
        except Exception as e:
            last_err = e
    raise last_err


def generate_titles_grouped_by_persona_fast(
    client: OpenAI,
    request: Dict[str, Any],
    result: Dict[str, Any],
    n_titles_per_persona: int = 7,
) -> Dict[str, Any]:
    company = request["company"]
    personas = request["personas"]
    subreddits = request["subreddits"]

    if not personas:
        raise ValueError("No personas in request.json")
    if not subreddits:
        raise ValueError("No subreddits in request.json")

    hints = cluster_hints(result)
    cluster_catalog = build_cluster_catalog(result)

    valid_cluster_ids = {
        int(c["cluster_id"]) for c in (result.get("clusters") or []) if "cluster_id" in c
    }
    valid_cluster_ids_list = sorted(valid_cluster_ids)

    payload = {
        "meta": {
            "company": company["name"],
            "n_titles_per_persona": n_titles_per_persona,
            "model_candidates": MODEL_CANDIDATES,
        },
        "personas": [],
    }

    for persona in personas:
        prompt = build_persona_titles_prompt(
            company, persona, subreddits, hints, n_titles_per_persona, cluster_catalog
        )
        raw = call_with_fallback(client, prompt)
        obj = parse_json_loose(raw)

        arc_label = str(obj.get("arc_label", "persona arc")).strip()
        items = obj.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError("Model did not return items list")

        cleaned = []
        for i, it in enumerate(items[:n_titles_per_persona]):
            cid = it.get("cluster_id", None)
            try:
                cid = int(cid) if cid is not None else None
            except Exception:
                cid = None

            if cid is None or (valid_cluster_ids and cid not in valid_cluster_ids):
                cid = valid_cluster_ids_list[i % len(valid_cluster_ids_list)] if valid_cluster_ids_list else None

            cleaned.append(
                {
                    "index_in_persona": int(it.get("index_in_persona", i + 1)),
                    "subreddit": str(it.get("subreddit", subreddits[i % len(subreddits)])).strip(),
                    "cluster_id": cid,
                    "keyword_ids": it.get("keyword_ids", []),
                    "title": str(it.get("title", "")).strip(),
                }
            )

        payload["personas"].append(
            {
                "persona_username": persona["persona_username"],
                "arc_label": arc_label,
                "n_titles": len(cleaned),
                "titles": cleaned,
            }
        )

    return payload


def main(company_dir: str, n_titles_per_persona: int = 7):
    p = Path(company_dir)

    request = read_json(p / "request.json")
    clusters = read_json(p / "clusters.json")

    # OpenAI SDK will read OPENAI_API_KEY from environment automatically
    # If it's missing, fail with a clear message
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY is not set in environment")

    client = OpenAI()

    out = generate_titles_grouped_by_persona_fast(
        client=client,
        request=request,
        result=clusters,
        n_titles_per_persona=n_titles_per_persona,
    )

    out_path = p / "titles.json"
    write_json(out_path, out)
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    company_dir_arg = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) >= 3 else 7
    main(company_dir_arg, n_titles_per_persona=n)
