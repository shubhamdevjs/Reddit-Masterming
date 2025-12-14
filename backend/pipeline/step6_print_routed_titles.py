import json
import sys
from pathlib import Path
from typing import Any, Dict


def read_json(p: Path) -> Dict[str, Any]:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def main(company_dir: str):
    p = Path(company_dir)
    routed = read_json(p / "titles_routed.json")

    print("\nPer persona detailed output")
    for person in routed.get("personas", []):
        persona_user = person.get("persona_username", "")
        persona_info = person.get("info", "") or person.get("persona_info", "")

        print("\n" + "=" * 90)
        print("Persona:", persona_user)
        if persona_info:
            preview = persona_info[:220].replace("\n", " ")
            print("Info preview:", preview + ("..." if len(persona_info) > 220 else ""))

        for t in person.get("titles", []):
            title = t.get("title", "")
            assigned_sr = t.get("subreddit_assigned", "")

            cluster_id = t.get("cluster_id", None)
            cluster_theme = t.get("cluster_theme", None)
            keyword_ids = t.get("keyword_ids", None)

            print("\nTitle:", title)
            print("Assigned subreddit:", assigned_sr)

            if cluster_id is not None:
                print("Cluster:", cluster_id)
            if cluster_theme:
                print("Cluster theme:", cluster_theme)
            if keyword_ids:
                print("Cluster keyword_ids:", keyword_ids)

            cands = t.get("subreddit_candidates", [])
            if cands:
                top3 = [(c.get("subreddit", ""), round(float(c.get("score", 0.0)), 3)) for c in cands]
                print("Top candidates:", top3)


if __name__ == "__main__":
    main(sys.argv[1])
