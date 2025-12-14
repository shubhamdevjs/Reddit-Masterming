import json
import sys
from pathlib import Path

def main(company_dir: str):
    company_path = Path(company_dir)
    inputs_path = company_path / "input_payload.json"

    if not inputs_path.exists():
        raise FileNotFoundError("inputs.json not found")

    data = json.loads(inputs_path.read_text(encoding="utf-8"))

    # minimal validation
    if not data.get("company_name"):
        raise ValueError("company_name missing")
    if not data.get("company_description"):
        raise ValueError("company_description missing")

    request = {
        "company": {
            "name": data["company_name"],
            "description": data["company_description"]
        },
        "keywords": data["keywords"],
        "subreddits": data["subreddits"],
        "personas": data["personas"],
        "target_posts_per_week": data["target_posts_per_week"]
    }

    out_path = company_path / "request.json"
    out_path.write_text(json.dumps(request, indent=2), encoding="utf-8")

    print("STEP 0 DONE → request.json created")

if __name__ == "__main__":
    main(sys.argv[1])
