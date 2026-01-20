from __future__ import annotations
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os, time
from dotenv import load_dotenv
from openai import OpenAI
import yaml
from pathlib import Path
import chromadb, json
from style_loader import load_letter_texts, build_style_examples
from museum_api import fetch_artwork_metadata, RijksCache
from build_chroma_db import embed
from question_answering import *

# Load environment variables from .env file
load_dotenv()

# Load configuration
cfg = yaml.safe_load(Path("configs/config.yml").read_text(encoding="utf-8"))

# Globals
RIJKS_CACHE = RijksCache()
RIJKS_META = None

with open("Data/extracted_data.json", "r", encoding="utf-8") as f:
    EXTRACTED_DATA = json.load(f)
STYLE_TEXTS = []
STYLE_EXAMPLES = []

def build_artworks_from_json(extracted_data):
    """Transform extracted_data.json into ARTWORKS format for the app."""
    #
    artworks = {}
    for artwork_id, data in extracted_data.items():
        # Get the artist name - handle both simple string and nested structure
        artist = data.get("artist", "Unknown Artist")
        
        artworks[artwork_id] = {
            "id": artwork_id,
            "title": data.get("title", "Unknown"),
            "artist": artist,
            "year": data.get("year", ""),
            "image": f"/static/figs/{artwork_id}.png",  # Adjust path as needed
            "description": data.get("description", ""),
            "location": data.get("location", ""),
            "room": data.get("room", ""),
            "dimension": data.get("dimension", ""),
            "material": data.get("material", []),
            "source": data.get("source", ""),
            "initial_message": f"Welcome! I am {artist}. You are viewing my work '{data.get('title', 'this artwork')}'. What would you like to know?",
            "presets": [
                "What inspired this work?",
                "Tell me about your technique",
                "What was your artistic vision?",
                "What does this artwork mean?",
                "How long did this take to create?",
                "What is the story behind this?"
            ],
            "system_prompt": f"You are {artist}, speaking about your artwork '{data.get('title', 'this piece')}' from {data.get('year', 'this period')}. Speak as the artist would, sharing insights about techniques, symbolism, and artistic vision. Be warm, engaging, and historically accurate."
        }
    return artworks

ARTWORKS = build_artworks_from_json(EXTRACTED_DATA)

# FastAPI app setup with OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()

chroma = chromadb.PersistentClient(path="./db_rijksmuseum")
collection = chroma.get_or_create_collection("rijksmuseum_data")

# Startup event to fetch and cache Rijksmuseum metadata
@app.on_event("startup")
async def _startup():
    #name = ARTWORKS.get(artwork_id, ARTWORKS[artwork_id])["artist"]
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

sources = {
"Vincent van Gogh": [van_gogh_letters_path],
"Johannes Vermeer": [vermeer_texts_path],
}

persona_chunks = load_persona_chunks(sources)
# ============== ARTWORK CONFIGURATION ==============
# Each artwork has its own id, metadata, initial message, and suggested questions

MAX_QUESTIONS = 5  # Maximum questions per conversation

def reset_messages(request: Request, artwork_id: str):
    """Reset messages for specific artwork."""
    session_key = get_session_key(artwork_id)
    if session_key in request.session:
        del request.session[session_key]


def get_artwork(artwork_id: str, default=None):
    """Get artwork data by ID."""
    return ARTWORKS.get(artwork_id, default)


def get_session_key(artwork_id: str) -> str:
    """Generate session key for storing messages per artwork."""
    return f"messages_{artwork_id}"


def get_messages(request: Request, artwork_id: str) -> list[dict]:
    """Retrieve messages for specific artwork from session."""
    session_key = get_session_key(artwork_id)
    messages = request.session.get(session_key, [])
    
    if not messages:
        artwork = ARTWORKS.get(artwork_id)
        if artwork:
            messages = [{
                "role": "assistant",
                "content": artwork["initial_message"]
            }]
            request.session[session_key] = messages
    
    return messages


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
    response = client.responses.create(
        model="gpt-4o-mini",
        input=messages,   # chat-style list of dicts: [{"role": "...", "content": "..."}]
        store=False
    )
    return response.output_text


def build_messages(cfg: dict, style_examples: list[str], history: list[dict], name: str,rijks_meta: dict | None = None) -> list[dict]:
    """
    Build the message list for LLM API call.
    Note: history should already include the latest user message.
    """
    persona = cfg["persona"][name]
    system_prompt = persona["system_prompt"]

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

    rijks_block = ""
    if rijks_meta:
        p = rijks_meta.get("parsed") or {}
        rijks_block = f"""
RIJKSMUSEUM METADATA (ground truth - use as authoritative source):
If a user asks about techniques/materials and the answer is not present here, say you are not sure.
- objectNumber: {rijks_meta.get("objectNumber")}
- title: {p.get("title")}
- artist: {p.get("artist")}
- date: {p.get("date")}
- classified_as: {", ".join((p.get("classified_as") or [])[:20])}
- materials: {", ".join((p.get("materials") or [])[:20])}
- dimensions: {", ".join((p.get("dimensions") or [])[:20])}
- descriptions: {" | ".join((p.get("descriptions") or [])[:5])}

""".strip()

    dev_blocks = "\n\n---\n\n".join([b for b in [rijks_block, style_block] if b])

    return [
        {"role": "system", "content": system_prompt},
        {"role": "developer", "content": dev_blocks},
        *history,
    ]

def get_preset_responses() -> list[str]:
    """Return preset prompts for quickstart."""
    return [
        "What inspired you to create this?",
        "Tell me about your painting technique",
        "What symbolism is hidden in this work?",
        "How long did this take to paint?",
        "What was your life like during this time?",
        "How did you choose the colors?"
    ]

# ============== ROUTES ==============

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with artwork gallery."""
    return templates.TemplateResponse("index_2.html", {"request": request, "artworks": ARTWORKS})



@app.get("/chat/{artwork_id}/reset")
async def chat_reset(request: Request, artwork_id: str):
    """Reset chat history and redirect to home."""
    reset_messages(request, artwork_id)
    return RedirectResponse(url="/", status_code=303)


@app.get("/chat/{artwork_id}", response_class=HTMLResponse)
async def chat_get(request: Request, artwork_id: str):
    """Display chat page for specific artwork."""
    print(f"Requested artwork_id: {artwork_id}")
    artwork = get_artwork(artwork_id, {})
    print(f"Loading chat for artwork: {artwork_id}")
    print(f"Artwork data: {artwork}")
    
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


@app.post("/chat/{artwork_id}")
async def chat_api(request: Request, artwork_id: str, user_message: str = Form(...)):
    """
    AJAX endpoint for chat - returns JSON instead of HTML redirect
    """
    artwork = get_artwork(artwork_id)
    if not artwork:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": "artwork_not_found",
                "message": f"Artwork {artwork_id} not found."
            }
        )
    
    name = artwork["artist"]
    #print(f"Chat API - Artwork: {artwork_id}, Artist: {name}")
    
    messages = get_messages(request, artwork_id)
    session_key = get_session_key(artwork_id)
    
    if user_message and user_message.strip():
        messages.append({"role": "user", "content": user_message})
    
    try:
        # Check if limit reached
        if is_limit_reached(messages):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "limit_reached",
                    "message": f"You've reached the maximum of {MAX_QUESTIONS} questions."
                }
            )
        
        # Get artwork metadata from extracted_data
        # Build metadata block from our JSON data
        metadata_block = {
            "objectNumber": artwork_id,
            "parsed": {
                "title": artwork.get("title"),
                "artist": artwork.get("artist"),
                "date": artwork.get("year"),
                "materials": artwork.get("material", []),
                "dimensions": [artwork.get("dimension", "")],
                "descriptions": [artwork.get("description", "")],
                "classified_as": []
            }
        }
        
        # Merge with RIJKS_CACHE data if available
        cache_meta = RIJKS_CACHE.get()
        rijks_meta = cache_meta if cache_meta else metadata_block
        #print(messages)
        # Build full prompt with metadata
        #full_messages = build_messages(cfg, STYLE_EXAMPLES, messages, name=name, rijks_meta=rijks_meta)
        #full_messages = answer(user_message, artwork["title"], artwork["artist"], artwork_id, persona_chunks)
        # Generate response
        #assistant_response = generate_reply(full_messages)
        
        messages.append({"role": "user", "content": user_message})

        assistant_response = answer(
        query=user_message,
        title=artwork["title"],
        creator=artwork["artist"],
        painting_id=artwork_id,
        persona_chunks=persona_chunks,
        messages_history=messages  # ← Pass full conversation!
        )
        
        # Add to history
        messages.append({"role": "assistant", "content": assistant_response})
        request.session[session_key] = messages
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "response": assistant_response,
                "questions_remaining": get_questions_remaining(messages),
                "limit_reached": is_limit_reached(messages)
            }
        )
        
    except Exception as e:
        print(f"Error in chat_api: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "server_error",
                "message": "Something went wrong. Please try again."
            }
        )


# ============== DEBUG ENDPOINT ==============

@app.get("/debug/artworks")
def debug_artworks():
    """Debug endpoint to check artwork configuration."""
    return {
        "available_artworks": list(ARTWORKS.keys()),
        "style_examples_loaded": len(STYLE_EXAMPLES)
    }

@app.get("/debug/rijks_parsed")
def debug_rijks_parsed():
    meta = RIJKS_CACHE.get() or RIJKS_META
    return (meta or {}).get("parsed") or {}