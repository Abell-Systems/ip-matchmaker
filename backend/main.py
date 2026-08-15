"""Cloud Run entrypoint: wraps the ADK agent graph in a FastAPI app.

Local dev: uvicorn main:app --reload --port 8080
Cloud Run: this module is the container's entrypoint (see Dockerfile).
"""

import os

from dotenv import load_dotenv

load_dotenv()

from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=False,
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
