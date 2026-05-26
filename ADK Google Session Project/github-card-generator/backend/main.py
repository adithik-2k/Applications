from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from google.genai import types

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

from agent import github_card_agent


# -----------------------------------
# FastAPI App
# -----------------------------------
app = FastAPI(title="GitHub Dev Card Generator API")


# -----------------------------------
# CORS Middleware
# -----------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------
# ADK Services
# -----------------------------------
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()


# -----------------------------------
# ADK Runner
# -----------------------------------
runner = Runner(
    app_name="github-card-generator",
    agent=github_card_agent,
    session_service=session_service,
    memory_service=memory_service,
)


# -----------------------------------
# Static Files
# -----------------------------------
STATIC_DIR = Path("static")
CARDS_DIR = STATIC_DIR / "cards"

STATIC_DIR.mkdir(exist_ok=True)
CARDS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------------
# Request Model
# -----------------------------------
class GenerateRequest(BaseModel):
    username: str


# -----------------------------------
# Health Endpoint
# -----------------------------------
@app.get("/health")
async def health():
    return {"status": "healthy"}


# -----------------------------------
# Generate Dev Card
# -----------------------------------
@app.post("/generate")
async def generate(request: GenerateRequest):
    username = request.username.strip()

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required"
        )

    import uuid

    session_id = (
        f"session_{username}_{uuid.uuid4().hex[:8]}"
    )

    user_id = "web-user"

    try:
        # Create session first (FIX)
        await session_service.create_session(
            app_name="github-card-generator",
            user_id=user_id,
            session_id=session_id,
        )

        # Create proper ADK message
        from google.genai import types

        user_message = types.Content(
            role="user",
            parts=[
                types.Part(
                    text=f"Generate a dev card for GitHub user {username}"
                )
            ],
        )

        # Run ADK agent
        events = runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message,
        )

        final_response = ""

        # Read streamed events
        for event in events:
            if hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts"):
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_response += part.text

        # Expected generated file
        card_path = CARDS_DIR / f"{username}.html"

        if not card_path.exists():
            return {
                "status": "partial",
                "message": "Agent completed but card file was not created.",
                "agent_output": final_response,
            }

        return {
            "status": "success",
            "username": username,
            "card_url": f"/static/cards/{username}.html",
            "analysis_summary": final_response,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(e)}"
        )
# -----------------------------------
# View Card
# -----------------------------------
@app.get("/card/{username}")
async def get_card(username: str):
    file_path = CARDS_DIR / f"{username}.html"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Card not found"
        )

    return FileResponse(file_path)


# -----------------------------------
# Run Locally
# -----------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
    )

    from dotenv import load_dotenv
    import os

    load_dotenv()

    print("API KEY FOUND:", os.getenv("GOOGLE_API_KEY")[:10])
    print("GITHUB TOKEN FOUND:", os.getenv("GITHUB_TOKEN")[:10])