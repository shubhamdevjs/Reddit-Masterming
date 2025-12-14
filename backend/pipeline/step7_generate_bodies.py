import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

from openai import OpenAI


MODEL_CANDIDATES = ["gpt-4.1-mini", "gpt-4o-mini"]


def read_json(p: Path) -> Dict[str, Any]:
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: Dict[str, Any]) -> None:
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_json_loose(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        s, e = text.find("{"), text.rfind("}")
        if s != -1 and e != -1 and e > s:
            return json.loads(text[s : e + 1])
        raise


def call_with_fallback(client: OpenAI, prompt: str) -> str:
    last_err = None
    for m in MODEL_CANDIDATES:
        try:
            r = client.responses.create(
                model=m,
                input=prompt,
                max_output_tokens=120,
                temperature=0.4,
            )
            return r.output_text.strip()
        except Exception as e:
            last_err = e
    raise last_err


def infer_post_intent(title: str) -> str:
    t = (title or "").lower()
    if any(x in t for x in [" vs ", " versus ", "compare", "comparison"]):
        return "compare"
    if any(x in t for x in ["alternative", "alternatives"]):
        return "alternatives"
    if any(x in t for x in ["best", "recommend", "recommendation"]):
        return "recommendation"
    if any(x in t for x in ["how do i", "how to", "workflow", "faster", "automate", "automation"]):
        return "workflow_help"
    return "general_question"


def title_mentions_company(title: str, company_name: str) -> bool:
    return (company_name or "").lower() in (title or "").lower()


def build_body_prompt(
    company: Dict[str, str],
    persona: Dict[str, str],
    subreddit: str,
    title: str,
    intent: str,
    allow_company_mention: bool,
) -> str:
    company_rule = (
        f"You may mention {company['name']} only if it feels unavoidable from the title context."
        if allow_company_mention
        else f"Do not mention {company['name']} or any brand/product names."
    )

    return f"""
Write a Reddit post body that feels like a real OP. Keep it short.

Subreddit: {subreddit}
Title: {title}
Intent type: {intent}

Persona voice anchor:
username: {persona["persona_username"]}
info: {persona["info"]}

Company context (for background only):
{company["name"]}: {company["description"]}

Hard rules:
- Exactly 1 or 2 sentences.
- Sound like a normal Reddit post, not formal writing.
- Usually a question or a request for suggestions.
- No marketing language. No emojis. No call to action.
- {company_rule}

Output JSON only:
{{"body":"..."}}
""".strip()


def generate_bodies_1to2_sentences(
    client: OpenAI,
    request: Dict[str, Any],
    routed_payload: Dict[str, Any],
) -> Dict[str, Any]:
    company = request["company"]

    out = {
        "meta": {
            "body_length": "exactly 1-2 sentences",
            "models": MODEL_CANDIDATES,
        },
        "personas": [],
    }

    persona_lookup = {p["persona_username"]: p for p in request.get("personas", [])}

    for p in routed_payload.get("personas", []):
        pu = p.get("persona_username", "")
        pinfo = p.get("info") or persona_lookup.get(pu, {}).get("info", "")
        persona_ctx = {"persona_username": pu, "info": pinfo}

        persona_block = {"persona_username": pu, "titles": []}

        for t in p.get("titles", []):
            subreddit = t.get("subreddit_assigned") or t.get("subreddit") or ""
            title = t.get("title", "")
            intent = infer_post_intent(title)

            allow_company = title_mentions_company(title, company["name"])

            prompt = build_body_prompt(
                company=company,
                persona=persona_ctx,
                subreddit=subreddit,
                title=title,
                intent=intent,
                allow_company_mention=allow_company,
            )

            raw = call_with_fallback(client, prompt)
            try:
                body = parse_json_loose(raw).get("body", "").strip()
            except Exception:
                body = raw.strip().strip('"')

            sentences = re.split(r"(?<=[.!?])\s+", body.strip())
            body = " ".join(sentences[:2]).strip()

            persona_block["titles"].append({**t, "body": body})

        out["personas"].append(persona_block)

    return out


def main(company_dir: str):
    p = Path(company_dir)

    request = read_json(p / "request.json")
    routed = read_json(p / "titles_routed.json")

    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY is not set in environment")

    client = OpenAI()

    persona_posts_payload = generate_bodies_1to2_sentences(
        client=client,
        request=request,
        routed_payload=routed,
    )

    out_path = p / "posts_with_bodies.json"
    write_json(out_path, persona_posts_payload)
    print(f"Wrote: {out_path}")

    # Preview
    for person in persona_posts_payload.get("personas", [])[:2]:
        print(f"\nPersona: {person.get('persona_username','')}")
        for post in person.get("titles", [])[:3]:
            print("\nsubreddit:", post.get("subreddit_assigned") or post.get("subreddit"))
            print("title   :", post.get("title", ""))
            print("body    :", post.get("body", ""))


if __name__ == "__main__":
    main(sys.argv[1])
