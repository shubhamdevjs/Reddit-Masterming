from __future__ import annotations

import io
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# -------------------------
# FastAPI
# -------------------------
app = FastAPI(title="Reddit Campaign Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://localhost:3001", 
        "http://localhost:3002",
        "https://*.vercel.app",  # Allow all Vercel preview deployments
        os.getenv("FRONTEND_URL", "")  # Production frontend URL from env var
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
COMPANIES_DIR = BASE_DIR / "companies"
PIPELINE_DIR = BASE_DIR / "pipeline"


# -------------------------
# Models
# -------------------------
class KeywordItem(BaseModel):
    keyword_id: str
    keyword: str


class PersonaItem(BaseModel):
    persona_username: str
    info: str


class CampaignInput(BaseModel):
    company_name: str
    company_description: str
    target_posts_per_week: int
    subreddits: List[str]
    keywords: List[KeywordItem]
    personas: List[PersonaItem]


# -------------------------
# Helpers
# -------------------------
def safe_company_dir_name(company_name: str) -> str:
    name = (company_name or "").strip()
    if not name:
        raise ValueError("company_name is empty")
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)


def ensure_company_dir(company_name: str) -> Path:
    COMPANIES_DIR.mkdir(parents=True, exist_ok=True)
    d = COMPANIES_DIR / safe_company_dir_name(company_name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def run_step(step_script: str, company_dir: Path, *extra_args: str) -> None:
    """
    Runs: python pipeline/<step_script> <company_dir> [extra_args...]
    Uses the current interpreter (important for venv).
    """
    script_path = PIPELINE_DIR / step_script
    if not script_path.exists():
        raise FileNotFoundError(f"Missing pipeline script: {script_path}")

    cmd = [sys.executable, str(script_path), str(company_dir), *extra_args]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        msg = (
            f"Step failed: {step_script}\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )
        raise RuntimeError(msg)


def require_openai_key_for_llm_steps() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set in environment. Set it before calling this endpoint.",
        )


# -------------------------
# Routes
# -------------------------
@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/campaigns/create/v2")
async def create_campaign_v2(payload: CampaignInput):
    """
    New pipeline mode.
    1) Save request.json in companies/<company>/
    2) Run pipeline scripts in order
    3) Return final nested json path
    """
    try:
        company_dir = ensure_company_dir(payload.company_name)
        
        # Calculate company website
        company_website = payload.company_name.strip().lower().replace(" ", "") + ".com"

        request_obj = {
            "company": {
                "name": payload.company_name.strip(),
                "description": payload.company_description.strip(),
            },
            "keywords": [kw.dict() for kw in payload.keywords],
            "subreddits": [s.strip() for s in payload.subreddits if s and s.strip()],
            "personas": [p.dict() for p in payload.personas],
            "target_posts_per_week": int(payload.target_posts_per_week),
        }

        write_json(company_dir / "request.json", request_obj)
        write_json(company_dir / "input_payload.json", payload.dict())

        # LLM steps will fail without OPENAI_API_KEY
        require_openai_key_for_llm_steps()

        # Run your pipeline steps.
        # Adjust this list to match the exact filenames you created.
        # Based on our previous steps:
        run_step("step1_cluster.py", company_dir)
        run_step("step2_capacity.py", company_dir)
        run_step("step3_generate_titles.py", company_dir)
        run_step("step5_route_subreddits.py", company_dir)
        run_step("step7_generate_bodies.py", company_dir)
        run_step("step8_weekly_plan.py", company_dir)
        run_step("step9_assign_schedule.py", company_dir)
        run_step("step10_comment_plan.py", company_dir)
        run_step("step11_generate_comments.py", company_dir)
        run_step("step12_build_reddit_output.py", company_dir)
        run_step("step13_build_reddit_output_nested.py", company_dir)

        nested_path = company_dir / "reddit_output_nested.json"
        if not nested_path.exists():
            raise RuntimeError("Expected reddit_output_nested.json was not created")

        # Load the nested output data to return to frontend
        nested_data = json.loads(nested_path.read_text(encoding="utf-8"))

        return {
            "status": "success",
            "campaignId": company_dir.name,
            "outputDir": str(company_dir),
            "requestFile": str(company_dir / "request.json"),
            "nestedOutputFile": str(nested_path),
            "nestedData": nested_data,
            "campaign": {
                "company_name": payload.company_name.strip(),
                "company_description": payload.company_description.strip(),
                "company_website": company_website,
                "subreddits": payload.subreddits,
                "keywords": [kw.dict() for kw in payload.keywords],
                "personas": [p.dict() for p in payload.personas],
                "target_posts_per_week": int(payload.target_posts_per_week),
            },
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/campaigns/{campaign_id}")
def delete_campaign(campaign_id: str):
    """Delete a campaign and all its files"""
    try:
        import shutil
        campaign_dir = COMPANIES_DIR / campaign_id
        
        if not campaign_dir.exists():
            raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found")
        
        # Remove the entire campaign directory
        shutil.rmtree(campaign_dir)
        
        return {
            "status": "success",
            "message": f"Campaign '{campaign_id}' deleted successfully",
            "campaignId": campaign_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/campaigns/create/file")
async def create_campaign_from_file(file: UploadFile = File(...)):
    """
    Upload CSV or Excel and convert into CampaignInput-like request.json.
    Then run the same pipeline.
    """
    try:
        contents = await file.read()

        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Use CSV or Excel.")

        # Very simple extraction. Customize to your file layout.
        # Expected columns:
        # company_name, company_description, subreddit, persona_username, persona_info, keyword_id, keyword, target_posts_per_week
        cols = {c.lower().strip(): c for c in df.columns}

        def col(name: str) -> str:
            if name not in cols:
                raise HTTPException(status_code=400, detail=f"Missing column: {name}")
            return cols[name]

        company_name = str(df[col("company_name")].iloc[0]).strip()
        company_description = str(df[col("company_description")].iloc[0]).strip()
        target_posts_per_week = int(df[col("target_posts_per_week")].iloc[0])

        subreddits = sorted(set(str(x).strip() for x in df[col("subreddit")].dropna().tolist() if str(x).strip()))
        keywords = []
        for _, r in df[[col("keyword_id"), col("keyword")]].dropna().iterrows():
            keywords.append({"keyword_id": str(r[col("keyword_id")]).strip(), "keyword": str(r[col("keyword")]).strip()})

        personas_map: Dict[str, str] = {}
        for _, r in df[[col("persona_username"), col("persona_info")]].dropna().iterrows():
            u = str(r[col("persona_username")]).strip()
            info = str(r[col("persona_info")]).strip()
            if u and info and u not in personas_map:
                personas_map[u] = info

        personas = [{"persona_username": u, "info": info} for u, info in personas_map.items()]

        payload = CampaignInput(
            company_name=company_name,
            company_description=company_description,
            target_posts_per_week=target_posts_per_week,
            subreddits=subreddits,
            keywords=[KeywordItem(**k) for k in keywords],
            personas=[PersonaItem(**p) for p in personas],
        )

        # Reuse v2 endpoint logic
        return await create_campaign_v2(payload)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
