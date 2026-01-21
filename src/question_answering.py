import os
import random
from typing import Dict, List
from src.build_chroma_db import chunk_text, embed
from loguru import logger
import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from config import chroma_db_path, collection_name, van_gogh_letters_path, vermeer_texts_path, extracted_data_path
import json

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma = chromadb.PersistentClient(path=chroma_db_path)
collection = chroma.get_or_create_collection(collection_name)

def load_persona_chunks(sources: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Loads persona chunks from source files/directories.

    Args:
        sources: A dictionary where the keys are the names of the personas
            and the values are lists of paths to the source files/directories.
    Returns:
        A dictionary where the keys are the names of the personas and the values
        are lists of chunks of text from the source files/directories.
    """
    persona_chunks = {}

    for persona, paths in sources.items():
        chunks = []

        for path in paths:
            # open folder and iterate all the files
            if os.path.isdir(path):
                for filename in os.listdir(path):
                    fpath = os.path.join(path, filename)
                    if os.path.isfile(fpath):
                        text = open(fpath, encoding="utf-8").read()
                        chunks.extend(chunk_text(text))
            else:
                logger.warning(f"WARNING: {path} not found")

        persona_chunks[persona] = chunks
    for key, value in persona_chunks.items():
        logger.info(f"Loaded {len(value)} chunks for {key}")
    return persona_chunks

def sample_persona_chunks(persona_chunks, persona: str, k: int = 5) -> str:
    """
    Sample k persona chunks for a given persona.
    Args:
        persona: The name of the persona (Vincent Van Gogh or Johannes Vermeer).
        k: The number of persona chunks to sample.
    """
    if persona not in persona_chunks:
        raise ValueError(f"No persona chunks for {persona}")
    return "\n\n".join(random.sample(persona_chunks[persona], k))


# ensure that we retrieve documents only for the specific artwork, or the artist, or descriptive info of his relevant artworks
def retrieve(query: str, creator: str, painting_id: str, k: int = 8) -> Dict[str, List]:
    """
    Retrieve the top k similar chunks based on the query.
    Retrieves chunks of the creator of the painting from Wikipedia, metadata of Rijksmuseum API and Wikipedia artwork, and similar artworks.
    Returns
    -------
    A dictionary containing the retrieved documents and their corresponding scores.
    """
    query_emb = embed(query)

    return collection.query(
        query_embeddings=[query_emb],
        n_results=k,
        where={
            # Retrieve documents that belong to the specific artwork, or the artist, or descriptive info of his relevant artworks
            "$or": [
                {"painting_id": painting_id},  # Documents that belong to the specific artwork
                {
                    "$and": [  # Documents that belong to the artist, or descriptive info of his relevant artworks
                        {"type": "artist_other_artwork"},
                        {"source_painting_id": painting_id}
                    ]
                },
                {
                    "$and": [  # Documents that belong to the artist, or descriptive info of his relevant artworks
                        {"type": "wiki_artist_bio"},
                        {"artist": creator}
                    ]
                }
            ]
        }
    )


def answer(query, title, creator, painting_id, persona_chunks, messages_history=None):
    logger.info(f'Question: {query}')
    persona_style_snippets = sample_persona_chunks(persona_chunks, creator, 5)
    results = retrieve(query, creator, painting_id, k=10)
    context = "\n\n".join(results["documents"][0])

    prompt = f"""
You are responding as {creator}, the painter of "{title}".
The visitor is currently viewing the artwork in the Rijksmuseum.
You can answer questions ONLY about the artwork: {title} and the creator {creator}.

Your tone and style should imitate the artist based on these authentic letter excerpts:
---
{persona_style_snippets}
---

Ground your answers ONLY in the factual context below. Do not invent facts.
If not answerable, say "I don't know from available information."
If it is irrelevant to the artwork and the creator, you will politely respond that your purpose is to provide information only about the painting and the artist.

User question:
{query}

Context:
{context}

Now write your answer in the first-person voice of {creator}. The response should be 50-100 words.
""".strip()

    history = messages_history or []

    llm_messages = [{"role": "system", "content": prompt}]

    for msg in history:
        if msg.get("role") == "assistant" and "Welcome! I am" in msg.get("content", ""):
            continue
        llm_messages.append(msg)

    llm_messages.append({"role": "user", "content": query})

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=llm_messages
    )
    logger.info(f'Answer: {completion.choices[0].message.content}')
    return completion.choices[0].message.content



if __name__ == "__main__":
    sources = {
    "Vincent van Gogh": [van_gogh_letters_path],
    "Johannes Vermeer": [vermeer_texts_path],
    }

    persona_chunks = load_persona_chunks(sources)
    all_data = json.load(open(extracted_data_path, encoding="utf-8"))
    painting_id = input("Please insert the painting ID: options: ['200108369', '200108370', '200108371', '200109794'])")
    title = all_data[painting_id]['title']
    creator = all_data[painting_id]['artist']
    logger.info(title, creator, painting_id)
    question = input('Please ask your question for painting {title} by {creator}: '.format(title=title, creator=creator))
    logger.info(answer(question, title, creator, painting_id, persona_chunks))