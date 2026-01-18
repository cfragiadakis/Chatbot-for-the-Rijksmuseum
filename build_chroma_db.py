from config import save_path, chroma_db_path, collection_name
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
import textwrap
from loguru import logger

all_data = json.load(open(save_path, encoding="utf-8"))
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma = chromadb.PersistentClient(path=chroma_db_path)
collection = chroma.get_or_create_collection(collection_name)

def chunk_text(text, size=800):
    """
    Break up a long text into smaller chunks of text.
    The text is broken up into chunks of a specified size.
    """
    text = text.replace("\n", " ")
    return textwrap.wrap(text, size)

def prepare_chunks(painting):
    """
    Break up a painting's information into smaller chunks of text.

    The function takes a painting's data and breaks it up into smaller chunks of text.
    The chunks of text are of three types: metadata, curatorial and wiki_painting.
    """
    chunks = []

    # Create a metadata chunk
    meta = f"""
    Title: {painting['title']}
    Artist: {painting['artist']}
    Year: {painting['year']}
    Room: {painting['room']}
    Location: {painting['location']}
    Material: {painting['material']}
    Dimensions: {painting['dimension']}
    """
    chunks.append({"type": "metadata", "text": meta})

    # Break up the description of Rijksmuseum into smaller chunks
    chunks.extend({"type": "curatorial", "text": c} 
                  for c in chunk_text(painting["description"]))

    # Break up the wikipedia artwork text into smaller chunks
    chunks.extend({"type": "wiki_painting", "text": c}
                  for c in chunk_text(painting["wiki_artwork"]))

    return chunks

def embed(text):
    """
    Embed a piece of text into a numerical vector.
    Takes a piece of text and embeds it into a numerical vector using the text-embedding-3-large model.
    """
    resp = client.embeddings.create(
        model="text-embedding-3-large",
        input=text)
    return resp.data[0].embedding

def index_artist_bio(painting):
    """
    Index the artist info from wiki.

    The function takes a painting's data and indexes the artist's info from wiki.
    The artist's info is broken up into smaller chunks of text and each chunk is indexed along with the painting's id.
    """
    # Get the artist's name
    artist = painting['artist']

    # Break up the artist's wiki text into smaller chunks
    bio_chunks = chunk_text(painting['wiki_artist'])

    # Iterate over each chunk and index it
    for i, chunk in enumerate(bio_chunks):
        chunk_id = f"artist_{artist}_{i}"

        collection.upsert(
            ids=[chunk_id],
            embeddings=[embed(chunk)],
            metadatas=[{
                "artist": artist,
                "type": "wiki_artist_bio"
            }],
            documents=[chunk]
        )

def index_artist_artworks(painting, painting_id):
    """
    Index the other artworks of the artist in the Rijksmuseum
    """
    artist = painting["artist"]

    # Iterate over each artwork of the artist
    for i, art in enumerate(painting.get("artist_artworks", [])):
        # Create a text chunk for the artwork
        text = f"""
        Other artworks by the creator in the Rijksmuseum:
        Title: {art['title']}
        Artist: {art['artist']}
        Location: {art['location']}
        Room: {art['room']}
        """
        # Create a unique id for the chunk
        chunk_id = f"{painting_id}_artist_artwork_{i}"
        
        # Index the chunk
        collection.upsert(
            ids=[chunk_id],
            embeddings=[embed(text)],
            documents=[text],
            metadatas=[{
                "type": "artist_other_artwork",  # Type of the chunk
                "artist": artist,  # Artist of the artwork
                "source_painting_id": painting_id,  # Painting id of the artwork
                "artwork_title": art["title"]  # Title of the artwork

            }]
        )


def index_painting(painting, painting_id):
    """
    Index the whole painting with the 3 parts of information:
    Rijksmuseum data + wiki info of artwork,
    wiki info of the artist, relevant artworks of the artist
    """
    index_artist_bio(painting) # Index the wiki info of the artist
    
    chunks = prepare_chunks(painting) # Prepare chunks of the painting
    
    # Iterate over each chunk
    for i, chunk in enumerate(chunks):
        chunk_id = f"{painting_id}_{i}" # Create a unique id for the chunk
        
        collection.upsert(
            ids=[chunk_id],
            embeddings=[embed(chunk["text"])],
            documents=[chunk["text"]],
            metadatas=[{
                "painting_id": painting_id, # Painting id of the chunk
                "title": painting["title"], # Title of the painting
                "artist": painting["artist"], # Artist of the painting
                "type": chunk["type"] # Type of the chunk
            }]
        )
    index_artist_artworks(painting, painting_id)  # Index the other artworks of the artist in the Rijksmuseum


def start_indexing(collection, all_data):
    """
    Start indexing the paintings in the Rijksmuseum collection
    Args:
        collection (Collection): The collection to index
        all_data (dict): The data of all paintings in the Rijksmuseum collection
    """
    indexed_ids = set(collection.get()['ids']) # Get the ids of the paintings that are already indexed

    # Iterate over each painting
    for painting_id, painting in all_data.items():

        prefix = painting_id + "_"  # check if any chunk for this painting exists using prefix match
        if any(cid.startswith(prefix) for cid in indexed_ids):
            logger.info(f"✔ Already indexed: {painting_id}") # Print a message if the painting is already indexed
            continue # Skip the painting if it is already indexed

        logger.info(f"Indexing: {painting_id}") # Print a message if the painting is being indexed
        index_painting(painting, painting_id) # Index the painting
        
    logger.info('Indexing Complete!')

if __name__ == '__main__':
    start_indexing(collection, all_data)    