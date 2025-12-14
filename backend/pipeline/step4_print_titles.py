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

    # not strictly required to print, but kept to match your workflow
    _request = read_json(p / "request.json")
    _clusters = read_json(p / "clusters.json")

    titles_payload = read_json(p / "titles.json")

    for person in titles_payload.get("personas", []):
        print(f"\nPersona: {person.get('persona_username')} ({person.get('n_titles')} titles)")
        for t in person.get("titles", []):
            print(f"  {t.get('index_in_persona')}. [{t.get('subreddit')}] {t.get('title')}")

if __name__ == "__main__":
    main(sys.argv[1])
