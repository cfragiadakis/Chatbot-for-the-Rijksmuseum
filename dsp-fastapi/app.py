from __future__ import annotations
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
from openai import OpenAI
import yaml
from pathlib import Path
from style_loader import load_letter_texts, build_style_examples

# Load environment variables from .env file
load_dotenv()

# Load configuration
cfg = yaml.safe_load(Path("configs/config.yml").read_text(encoding="utf-8"))

STYLE_TEXTS = []
STYLE_EXAMPLES = []

if cfg.get("style_examples", {}).get("enabled", False):
    STYLE_TEXTS = load_letter_texts(cfg)
    STYLE_EXAMPLES = build_style_examples(cfg, STYLE_TEXTS)

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



def build_messages(cfg: dict, style_examples: list[str], history: list[dict], user_text: str) -> list[dict]:
    system_prompt = cfg["persona"]["system_prompt"]

    anti_copy = "\n".join(f"- {r}" for r in cfg["style_examples"]["anti_copy_rules"])
    examples = "\n\n".join([f"EXAMPLE {i+1}:\n{ex}" for i, ex in enumerate(style_examples)])

    style_block = f"""
    Use the following excerpts ONLY to imitate writing style (tone, rhythm, word choice).
    Do not copy text directly.

    ANTI-COPY RULES:
    {anti_copy}

    STYLE EXAMPLES:
    {examples}
    """.strip()
   

    # Important: keep 'history' free of system/developer roles if you already add them here
    return [
        {"role": "system", "content": system_prompt},
        {"role": "developer", "content": style_block},
        *history,
        {"role": "user", "content": user_text},
    ]



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
            messages_for_llm = build_messages(cfg, STYLE_EXAMPLES, messages, user_input.strip())
            assistant_text = generate_reply(messages_for_llm)
        except Exception as e:
            assistant_text = f"(LLM error) {type(e).__name__}: {e}"

        messages.append({"role": "assistant", "content": assistant_text})
        request.session["messages"] = messages

    return RedirectResponse(url="/chat", status_code=303)

@app.get('/vangogh', response_class=HTMLResponse)
async def vangogh(request: Request):
    messages = get_messages(request)
    return templates.TemplateResponse(
        "vangogh.html",
        {"request": request, "messages": messages, "presets": list(PRESETS.keys())},
    )

@app.get('/chatvg', response_class=HTMLResponse)
async def chat_get(request: Request):
    messages = get_messages(request)
    return templates.TemplateResponse(
        "chat_vg.html",
        {"request": request, "messages": messages, "presets": list(PRESETS.keys())},
    )

@app.post('/chatvg', response_class=HTMLResponse)
async def chat_post(
    request: Request,
    user_input: str | None = Form(None),
    preset: str | None = Form(None),
    action: str | None = Form(None),
):
    messages = get_messages(request)
    if user_input and user_input.strip():
        messages.append({"role": "user", "content": user_input.strip()})
        try:
            messages_for_llm = build_messages(cfg, STYLE_EXAMPLES, messages, user_input.strip())
            assistant_text = generate_reply(messages_for_llm)
        except Exception as e:
            assistant_text = f"(LLM error) {type(e).__name__}: {e}"

        messages.append({"role": "assistant", "content": assistant_text})
        request.session["messages"] = messages

    return RedirectResponse(url="/chatvg", status_code=303)

# Debug endpoint to check if style examples are loaded
@app.get("/debug/style")
def debug_style():
    return {
        "num_examples": len(STYLE_EXAMPLES),
        "preview": STYLE_EXAMPLES[0][:250] if STYLE_EXAMPLES else None,
        "folder": cfg.get("style_examples", {}).get("folder")
    }