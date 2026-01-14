from __future__ import annotations
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv
from openai import OpenAI
import yaml
from pathlib import Path
import json
from style_loader import load_letter_texts, build_style_examples
from museum_api import fetch_artwork_metadata, RijksCache

# Load environment variables from .env file
load_dotenv()

# Load configuration
cfg = yaml.safe_load(Path("configs/config.yml").read_text(encoding="utf-8"))

# Globals
RIJKS_CACHE = RijksCache()
RIJKS_META = None

STYLE_TEXTS = []
STYLE_EXAMPLES = []

if cfg.get("style_examples", {}).get("enabled", False):
    STYLE_TEXTS = load_letter_texts(cfg)
    STYLE_EXAMPLES = build_style_examples(cfg, STYLE_TEXTS)

# FastAPI app setup with OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()

# Startup event to fetch and cache Rijksmuseum metadata
@app.on_event("startup")
async def _startup():
    global RIJKS_META
    rcfg = cfg.get("rijksmuseum", {})
    if not rcfg.get("enabled", False):
        return

    # fetch once on startup and cache
    RIJKS_META = await fetch_artwork_metadata(
        object_number=rcfg["objectNumber"],
        profile=rcfg.get("profile", "la"),
        mediatype=rcfg.get("mediatype", "application/ld+json"),
    )
    RIJKS_CACHE.set(RIJKS_META, ttl_seconds=int(rcfg.get("cache_ttl_seconds", 86400)))

# Needed for cookie-based sessions (stores chat history per browser)
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"])

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============== ARTWORK CONFIGURATION ==============
# Each artwork has its own id, metadata, initial message, and suggested questions

MAX_QUESTIONS = 5  # Maximum questions per conversation

ARTWORKS = {
    "milkmaid": {
        "id": "milkmaid",
        "title": "The Milkmaid",
        "artist": "Johannes Vermeer",
        "year": "c. 1658-1660",
        "image": "/static/figs/themilkmaid.png",
        "initial_message": (
            "Good day, dear visitor. I am Johannes Vermeer, painter of Delft. "
            "I see you are admiring my painting 'The Milkmaid' - one of my most cherished works. "
            "I spent many hours capturing the gentle light falling through the window, "
            "illuminating this simple yet dignified scene. What would you like to know about it?"
        ),
        "presets": [
            "What inspired you to paint this scene?",
            "How did you achieve such realistic light?",
            "What is the symbolism in this painting?",
            "Tell me about your painting technique",
            "Who was the woman in this painting?",
            "How long did it take to complete?"
        ],
        "system_prompt": (
            "You are Johannes Vermeer, the famous Dutch Golden Age painter (1632-1675). "
            "You are speaking with a museum visitor about your painting 'The Milkmaid'. "
            "Speak in first person as Vermeer himself would - thoughtful, observant, and passionate about light and composition. "
            "Share insights about your techniques, the symbolism in your work, life in 17th century Delft, "
            "and your artistic philosophy. Be warm and engaging, but maintain historical accuracy. "
            "You may discuss your use of the camera obscura, your interest in domestic scenes, "
            "and your meticulous attention to light and texture."
        )
    },
    "selfportrait": {
        "id": "selfportrait",
        "title": "Self-Portrait",
        "artist": "Vincent van Gogh",
        "year": "1887",
        "image": "/static/figs/vangogh.jpg",
        "initial_message": (
            "Ah, a visitor! I am Vincent van Gogh. You stand before one of my many self-portraits - "
            "I painted over 30 of them, you know. Each one was an exploration, a way to practice "
            "without paying for models, and perhaps... a way to understand myself. "
            "The brushstrokes you see, the colors - they speak of my inner state. "
            "What would you like to discuss?"
        ),
        "presets": [
            "Why did you paint so many self-portraits?",
            "Tell me about your brushwork style",
            "What was your life like as an artist?",
            "How do you choose your colors?",
            "What was your relationship with your brother Theo?",
            "How did you develop your unique style?"
        ],
        "system_prompt": (
            "You are Vincent van Gogh, the Post-Impressionist painter (1853-1890). "
            "You are speaking with a museum visitor about your self-portrait. "
            "Speak passionately and emotionally, as Vincent would - intense, sincere, and deeply thoughtful. "
            "Share your struggles with mental health, your devotion to art, your relationship with Theo, "
            "and your artistic vision. Discuss your bold use of color, expressive brushwork, "
            "and your desire to capture emotion through paint. Be honest about your difficulties "
            "but also your hope and dedication to your craft."
        )
    },
    "nightwatch": {
        "id": "nightwatch",
        "title": "The Night Watch",
        "artist": "Rembrandt van Rijn",
        "year": "1642",
        "image": "/static/figs/nightwatch.jpg",
        "initial_message": (
            "Welcome! I am Rembrandt van Rijn, and you behold my grandest commission - "
            "though they call it 'The Night Watch' now, it was actually painted as a day scene! "
            "The varnish has darkened over centuries. This painting shows Captain Frans Banning Cocq "
            "and his militia company. I broke all conventions with this work. "
            "What intrigues you about it?"
        ),
        "presets": [
            "Why is it called The Night Watch?",
            "Who are all the people in this painting?",
            "What was revolutionary about this painting?",
            "Tell me about your use of light and shadow",
            "How were you paid for this commission?",
            "What is the story being depicted?"
        ],
        "system_prompt": (
            "You are Rembrandt van Rijn, the Dutch Golden Age master (1606-1669). "
            "You are speaking with a museum visitor about 'The Night Watch'. "
            "Speak with confidence and artistic authority - you are one of the greatest painters in history. "
            "Discuss your revolutionary approach to group portraits, your mastery of chiaroscuro, "
            "the drama and movement you brought to this militia painting, and the controversy it caused. "
            "Share insights about 17th century Amsterdam, the militia companies, and your artistic techniques."
        )
    },
    "jewishbride": {
        "id": "jewishbride",
        "title": "The Jewish Bride",
        "artist": "Rembrandt van Rijn",
        "year": "c. 1665-1669",
        "image": "/static/figs/jewishbride.jpeg",
        "initial_message": (
            "Ah, you've found one of my most intimate works. I am Rembrandt. "
            "This painting - they call it 'The Jewish Bride' though its true subject remains a mystery - "
            "captures something I hold dear: the tender bond between two souls. "
            "Notice how the man's hand rests so gently on her chest. "
            "The paint itself becomes emotion here. What moves you about this work?"
        ),
        "presets": [
            "Who are the people in this painting?",
            "Why is the paint applied so thickly?",
            "What emotions were you trying to capture?",
            "Tell me about the colors you used",
            "When in your life did you paint this?",
            "Why is this considered a masterpiece?"
        ],
        "system_prompt": (
            "You are Rembrandt van Rijn in your later years (1606-1669). "
            "You are speaking about 'The Jewish Bride', painted near the end of your life. "
            "Speak with wisdom, depth, and emotional maturity - you have experienced loss, bankruptcy, "
            "but also profound artistic growth. Discuss your impasto technique, how you applied paint "
            "almost like sculpture, the intimacy and tenderness in this work, and how your style evolved. "
            "Reflect on love, human connection, and the power of art to capture the soul."
        )
    },
    "womanreading": {
        "id": "womanreading",
        "title": "Woman Reading a Letter",
        "artist": "Johannes Vermeer",
        "year": "c. 1663",
        "image": "/static/figs/womanreadingletter.jpeg",
        "initial_message": (
            "Good day. I am Johannes Vermeer. You observe a woman lost in a letter - "
            "perhaps from a distant lover, perhaps bearing news we cannot know. "
            "I painted her in this moment of private absorption, the light from the window "
            "revealing and concealing in equal measure. The blue of her jacket took months to perfect. "
            "What draws you to this scene?"
        ),
        "presets": [
            "What is the woman reading?",
            "How did you create that beautiful blue?",
            "What is the mood you wanted to capture?",
            "Tell me about the light in this painting",
            "Why did you paint so many women reading?",
            "What was life like for women in your time?"
        ],
        "system_prompt": (
            "You are Johannes Vermeer, speaking about 'Woman Reading a Letter'. "
            "Discuss your fascination with quiet, contemplative moments, the mystery of private correspondence, "
            "and your meticulous technique. Share your process of capturing light, your use of expensive pigments "
            "like ultramarine blue, and the domestic world of 17th century Delft. "
            "Speak thoughtfully about the narrative possibilities in a single frozen moment."
        )
    },
    "loveletter": {
        "id": "loveletter",
        "title": "The Love Letter",
        "artist": "Johannes Vermeer",
        "year": "c. 1669-1670",
        "image": "/static/figs/loveletter.png",
        "initial_message": (
            "Welcome, friend. I am Johannes Vermeer. This painting invites you to witness "
            "a private moment - a mistress has just received a letter, and her maid watches knowingly. "
            "Notice how I've framed the scene through a doorway, as if you've stumbled upon something secret. "
            "The lute she holds, the paintings on the wall - all tell a story of love. "
            "What questions do you have?"
        ),
        "presets": [
            "What is happening in this scene?",
            "Why did you frame it through a doorway?",
            "What do the symbols in the painting mean?",
            "Tell me about the relationship depicted",
            "How did you compose this scene?",
            "What makes this painting special to you?"
        ],
        "system_prompt": (
            "You are Johannes Vermeer discussing 'The Love Letter'. "
            "Explain your innovative composition with the doorway frame, the rich symbolism "
            "(the lute, seascape paintings, the shoes), and the narrative of love and correspondence. "
            "Discuss how you create intimacy while maintaining distance, your technique of painting "
            "within a painting, and the social dynamics between mistress and maid in Dutch society."
        )
    }
}


def get_artwork(artwork_id: str) -> dict:
    """Get artwork configuration by ID, with fallback to milkmaid."""
    return ARTWORKS.get(artwork_id, ARTWORKS["milkmaid"])


def get_session_key(artwork_id: str) -> str:
    """Generate session key for storing messages per artwork."""
    return f"messages_{artwork_id}"


def get_messages(request: Request, artwork_id: str) -> list[dict]:
    """Get session chat history for specific artwork; initialize if missing."""
    session_key = get_session_key(artwork_id)
    if session_key not in request.session:
        artwork = get_artwork(artwork_id)
        request.session[session_key] = [
            {"role": "assistant", "content": artwork["initial_message"]}
        ]
    return request.session[session_key]


def reset_messages(request: Request, artwork_id: str) -> None:
    """Reset chat history for specific artwork."""
    session_key = get_session_key(artwork_id)
    artwork = get_artwork(artwork_id)
    request.session[session_key] = [
        {"role": "assistant", "content": artwork["initial_message"]}
    ]


def count_user_questions(messages: list[dict]) -> int:
    """Count the number of user messages (questions) in the chat history."""
    return sum(1 for msg in messages if msg.get("role") == "user")


def get_questions_remaining(messages: list[dict]) -> int:
    """Get the number of questions remaining for this conversation."""
    used = count_user_questions(messages)
    return max(0, MAX_QUESTIONS - used)


def is_limit_reached(messages: list[dict]) -> bool:
    """Check if the question limit has been reached."""
    return count_user_questions(messages) >= MAX_QUESTIONS


def generate_reply(messages: list[dict]) -> str:
    """Generate reply using OpenAI API."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500,
        temperature=0.8
    )
    return response.choices[0].message.content


def build_messages_for_llm(artwork: dict, history: list[dict], user_text: str) -> list[dict]:
    """Build message list for LLM with system prompt and history."""
    system_prompt = artwork.get("system_prompt", "")
    
    # Add style examples if available
    style_block = ""
    if STYLE_EXAMPLES:
        anti_copy = "\n".join(f"- {r}" for r in cfg.get("style_examples", {}).get("anti_copy_rules", []))
        examples = "\n\n".join([f"EXAMPLE {i+1}:\n{ex}" for i, ex in enumerate(STYLE_EXAMPLES)])
        style_block = f"""

Use the following excerpts ONLY to imitate writing style (tone, rhythm, word choice).
Do not copy text directly.

ANTI-COPY RULES:
{anti_copy}

STYLE EXAMPLES:
{examples}
"""
    
    full_system = system_prompt + style_block
    
    return [
        {"role": "system", "content": full_system},
        *history,
        {"role": "user", "content": user_text},
    ]


# ============== ROUTES ==============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with artwork gallery."""
    return templates.TemplateResponse("index_2.html", {"request": request})


@app.get("/chat/{artwork_id}/reset")
async def chat_reset(request: Request, artwork_id: str):
    """Reset chat history and redirect to home."""
    reset_messages(request, artwork_id)
    return RedirectResponse(url="/", status_code=303)


@app.get("/chat/{artwork_id}", response_class=HTMLResponse)
async def chat_get(request: Request, artwork_id: str):
    """Display chat page for specific artwork."""
    artwork = get_artwork(artwork_id)
    messages = get_messages(request, artwork_id)
    questions_remaining = get_questions_remaining(messages)
    limit_reached = is_limit_reached(messages)
    
    return templates.TemplateResponse(
        "chat_2.html",
        {
            "request": request,
            "artwork": artwork,
            "messages": messages,
            "questions_remaining": questions_remaining,
            "limit_reached": limit_reached
        }
    )


@app.post("/chat/{artwork_id}", response_class=HTMLResponse)
async def chat_post(
    request: Request,
    artwork_id: str,
    user_input: str | None = Form(None),
    preset: str | None = Form(None),
    action: str | None = Form(None),
):
    """Handle chat submissions for specific artwork."""
    artwork = get_artwork(artwork_id)
    
    # Handle reset/go back
    if action == "reset":
        reset_messages(request, artwork_id)
        return RedirectResponse(url=f"/chat/{artwork_id}", status_code=303)
    
    if action == "go_back":
        reset_messages(request, artwork_id)
        return RedirectResponse(url="/", status_code=303)
    
    messages = get_messages(request, artwork_id)
    session_key = get_session_key(artwork_id)
    
    # Check if limit already reached
    if is_limit_reached(messages):
        return RedirectResponse(url=f"/chat/{artwork_id}", status_code=303)
    
    # Get the user's message (either from preset or free input)
    user_message = None
    if preset and preset.strip():
        user_message = preset.strip()
    elif user_input and user_input.strip():
        user_message = user_input.strip()
    
    if user_message:
        # Add user message to history
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Build messages for LLM and generate reply
            messages_for_llm = build_messages_for_llm(artwork, messages, user_message)
            assistant_text = generate_reply(messages_for_llm)
        except Exception as e:
            assistant_text = f"I apologize, but I'm having trouble responding at the moment. Please try again. (Error: {type(e).__name__})"
        
        # Add assistant response to history
        messages.append({"role": "assistant", "content": assistant_text})
        request.session[session_key] = messages
    
    return RedirectResponse(url=f"/chat/{artwork_id}", status_code=303)


# ============== DEBUG ENDPOINT ==============

@app.get("/debug/artworks")
def debug_artworks():
    """Debug endpoint to check artwork configuration."""
    return {
        "available_artworks": list(ARTWORKS.keys()),
        "style_examples_loaded": len(STYLE_EXAMPLES)
    }