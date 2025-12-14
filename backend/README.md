redditfast_prod

What this is
- Converts your notebook logic into a small Python package + CLI that generates a week-wise Reddit posting plan.
- Output formats:
  - JSON (week-wise, includes posts + comments)
  - XLSX (posts + comments sheets)

Setup
1) Create a venv and install deps:
   pip install -r requirements.txt

2) Put your API key in an environment variable (recommended):
   Windows PowerShell:
     $env:OPENAI_API_KEY="your_key"
   macOS/Linux:
     export OPENAI_API_KEY="your_key"

Run
- Save your combined keywords + subreddits text into a file, e.g. inputs/user_text.txt
- Save personas TSV into a file, e.g. inputs/personas.tsv

Then:
  python -m redditfast.cli --user-text inputs/user_text.txt --personas inputs/personas.tsv --posts-per-week 3 --weeks 4 --format both

Notes on API keys for production
- Do not hardcode keys in code or commit them to Git.
- In production, set OPENAI_API_KEY via your deployment environment:
  - Docker: pass with --env or an env file
  - ECS: store in Secrets Manager and map to an environment variable
  - GitHub Actions: store in GitHub Secrets and inject at runtime
