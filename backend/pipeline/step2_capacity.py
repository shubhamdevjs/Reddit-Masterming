import json
import sys
from pathlib import Path
from typing import Any, Dict


def load_request_or_build(company_dir: str) -> Dict[str, Any]:
    p = Path(company_dir)

    # 1) If request.json exists, use it
    request_path = p / "request.json"
    if request_path.exists():
        return json.loads(request_path.read_text(encoding="utf-8"))

    # 2) Else build request from inputs.json (same structure as step0)
    inputs_path = p / "input_payload.json"
    if not inputs_path.exists():
        raise FileNotFoundError(f"inputs.json not found at: {inputs_path}")

    data = json.loads(inputs_path.read_text(encoding="utf-8"))

    company_name = (data.get("company_name") or "").strip()
    company_description = (data.get("company_description") or "").strip()

    if not company_name:
        raise ValueError("company_name missing in inputs.json")
    if not company_description:
        raise ValueError("company_description missing in inputs.json")

    request = {
        "company": {"name": company_name, "description": company_description},
        "keywords": data.get("keywords", []),
        "subreddits": data.get("subreddits", []),
        "personas": data.get("personas", []),
        "target_posts_per_week": data.get("target_posts_per_week"),
    }
    return request


def compute_capacity_from_request(
    request: Dict[str, Any],
    A: int = 3,
    B: int = 2,
    C: int = 1,
    safety: float = 0.8,
) -> Dict[str, Any]:
    P = len(request["personas"])
    S = len(request["subreddits"])
    target = int(request["target_posts_per_week"])

    persona_capacity = P * A
    subreddit_capacity = S * B
    pair_capacity = P * S * C

    max_posts_raw = min(persona_capacity, subreddit_capacity, pair_capacity)
    max_posts_safe = int(max_posts_raw * safety)

    limiting = []
    if max_posts_raw == persona_capacity:
        limiting.append("persona_capacity")
    if max_posts_raw == subreddit_capacity:
        limiting.append("subreddit_capacity")
    if max_posts_raw == pair_capacity:
        limiting.append("pair_capacity")

    feasible_posts = min(target, max_posts_safe)

    return {
        "inputs": {
            "P": P,
            "S": S,
            "A": A,
            "B": B,
            "C": C,
            "safety": safety,
            "target_posts_per_week": target,
        },
        "capacities": {
            "persona_capacity": persona_capacity,
            "subreddit_capacity": subreddit_capacity,
            "pair_capacity": pair_capacity,
            "max_posts_raw": max_posts_raw,
            "max_posts_safe": max_posts_safe,
            "limiting_factors": limiting,
        },
        "final": {
            "feasible_posts_per_week": feasible_posts,
            "target_was_capped": target > max_posts_safe,
        },
    }


def main(company_dir: str):
    request = load_request_or_build(company_dir)

    capacity = compute_capacity_from_request(
        request,
        A=3,
        B=2,
        C=1,
        safety=0.8,
    )

    print("P:", capacity["inputs"]["P"])
    print("S:", capacity["inputs"]["S"])
    print("max_posts_raw:", capacity["capacities"]["max_posts_raw"])
    print("max_posts_safe:", capacity["capacities"]["max_posts_safe"])
    print("limiting_factors:", capacity["capacities"]["limiting_factors"])
    print("target:", capacity["inputs"]["target_posts_per_week"])
    print("feasible_posts_per_week:", capacity["final"]["feasible_posts_per_week"])
    print("target_was_capped:", capacity["final"]["target_was_capped"])

    out_path = Path(company_dir) / "capacity.json"
    out_path.write_text(json.dumps(capacity, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1])
