from __future__ import annotations

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# FastAPI app setup with OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()

# Needed for cookie-based sessions (stores chat history per browser)
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"])

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Chat defaults
INITIAL_MESSAGES = [
    {
        "role": "assistant",
        "content": (
            "Hello visitor, you are speaking with Johannes Vermeer. "
            "I am glad you are interested in my painting 'The Milkmaid', "
            "one of my favourite ones. What would you like to know about my artwork?"
        ),
    }
]

PRESETS = {
    "Who painted this artwork?": "Johannes Vermeer painted the Milkmaid.",
    "When was it created?": "It was created around 1657–1658.",
    "What is happening in the scene?": "A maid pours milk into a bowl, symbolizing domestic virtue.",
    "Why is this painting famous?": "It is known for its realism, light, and detailed textures.",
    "What materials were used?": "Oil paint on canvas.",
    "What symbolism does it contain?": "The bread and milk symbolize nourishment and humility.",
}


def get_messages(request: Request) -> list[dict]:
    """Get session chat history; initialize if missing."""
    if "messages" not in request.session:
        request.session["messages"] = INITIAL_MESSAGES.copy()
    return request.session["messages"]


def reset_messages(request: Request) -> None:
    request.session["messages"] = INITIAL_MESSAGES.copy()

def generate_reply(messages: list[dict]) -> str:
    response = client.responses.create(
        model="gpt-4o-mini",
        input=messages,   # chat-style list of dicts: [{"role": "...", "content": "..."}]
        store=False
    )
    return response.output_text

def trim_history(messages: list[dict], max_turns: int = 20) -> list[dict]:
    system = [m for m in messages if m["role"] == "system"]
    rest = [m for m in messages if m["role"] != "system"]
    return system + rest[-(max_turns * 2):]


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Equivalent to Streamlit's home page with background + Start Chat button
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat_get(request: Request):
    messages = get_messages(request)
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "messages": messages, "presets": list(PRESETS.keys())},
    )


@app.post("/chat", response_class=HTMLResponse)
async def chat_post(
    request: Request,
    user_input: str | None = Form(None),
    preset: str | None = Form(None),
    action: str | None = Form(None),
):
    # Handle "Go back" (reset + redirect)
    if action == "go_back":
        reset_messages(request)
        return RedirectResponse(url="/", status_code=303)

    messages = get_messages(request)

    # Handle preset buttons
    if preset and preset in PRESETS:
        messages.append({"role": "user", "content": preset})
        messages.append({"role": "assistant", "content": PRESETS[preset]})
        request.session["messages"] = messages
        return RedirectResponse(url="/chat", status_code=303)

    # Handle free text input
    if user_input and user_input.strip():
        messages.append({"role": "user", "content": user_input.strip()})
        try:
            assistant_text = generate_reply(trim_history(messages))
        except Exception as e:
            assistant_text = f"(LLM error) {type(e).__name__}: {e}"

        messages.append({"role": "assistant", "content": assistant_text})
        request.session["messages"] = messages

    return RedirectResponse(url="/chat", status_code=303)
