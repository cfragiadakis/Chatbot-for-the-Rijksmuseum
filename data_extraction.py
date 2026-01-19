import requests
import re
from config import search_set, folder_path, extracted_data_path
import json
from pathlib import Path
from loguru import logger

def search_portraits(title=None, creator=None, type='painting'):
    """
    Search for artworks in the Rijksmuseum collection based on title, creator, and type.

    Args:
        title (str): Title of the artwork
        creator (str): Creator of the artwork
        type (str): Type of the artwork (default: 'painting')

    Returns:
        dict: Results of the search as a dictionary
    """

    SEARCH_URL = "https://data.rijksmuseum.nl/search/collection"
    params = {
        "creator": creator, 
        "title": title,
        "imageAvailable": "true",
        "type": type
    }

    r = requests.get(SEARCH_URL, params=params)
    r.raise_for_status()
    data = r.json()

    return data

def parse_artwork_details(data: dict) -> dict:
    """
    Extracts useful structured fields from Rijksmuseum Linked.Art objects
    """
    
    en_code = "http://vocab.getty.edu/aat/300388277" # prefer English so there is no need to find a way for translation
    nl_code = "http://vocab.getty.edu/aat/300388256" # dutch language has more information

    unit_map = {
        "http://vocab.getty.edu/aat/300379098": "cm",
        "http://vocab.getty.edu/aat/300379226": "kg",
    }
    
    attr_map = {
        "https://id.rijksmuseum.nl/22011": "hoogte",
        "https://id.rijksmuseum.nl/22012": "breedte",
        "https://id.rijksmuseum.nl/220217": "gewicht",
    }

    # ------------ TITLE ------------
    # First look for Dutch version
    
    title = None
    for s in data.get("subject_of", []):
        for part in s.get("part", []):
            for sub in part.get("part", []):
                if sub.get("type") == "Name":
                    langs = sub.get("language", [])
                    if any(l.get("id") == en_code for l in langs):
                        title = sub.get("content")
                        break
            if title:
                break
        if title:
            break

    # fallback: take any title if no English was found
    if not title:
        for s in data.get("subject_of", []):
            for part in s.get("part", []):
                for sub in part.get("part", []):
                    if sub.get("type") == "Name":
                        title = sub.get("content")
                        break
                if title:
                    break
            if title:
                break

    # ------------ ARTIST / MAKER ------------
    artist_name = None
    artist_id = None
    
    prod = data.get("produced_by")
    if isinstance(prod, dict):
        for part in prod.get("part", []):
            # get the person URI
            for agent in part.get("carried_out_by", []):
                artist_id = agent.get("id")
    
            # read Dutch referred_to_by labels
            for ref in part.get("referred_to_by", []):
                if ref.get("type") == "LinguisticObject":
                    langs = ref.get("language", [])
                    if any(l.get("id") == en_code for l in langs):
                        artist_name = ref.get("content")
                        break
    
            # fallback: any referred_to_by without language filter
            if artist_name is None:
                for ref in part.get("referred_to_by", []):
                    if ref.get("type") == "LinguisticObject":
                        artist_name = ref.get("content")
                        break

    # ------------ YEAR ------------
    year = None
    ts = prod.get("timespan") if prod else None
    if isinstance(ts, dict):
        # Try identified_by textual year first
        if isinstance(ts.get("identified_by"), list):
            for ident in ts["identified_by"]:
                c = ident.get("content")
                if c and any(ch.isdigit() for ch in c):
                    year = c
                    break

        # fallback to machine timestamps
        if year is None:
            b = ts.get("begin_of_the_begin")
            if b: 
                year = b[:4]

    # ------------ DESCRIPTION ------------
    descriptions_nl = []

    for entry in data.get("subject_of", []):
        langs = entry.get("language", [])
        if not any(l.get("id") == en_code for l in langs):
            continue
    
        # level 1: direct content
        if "content" in entry:
            descriptions_nl.append(entry["content"])
    
        # level 2: parts
        for p in entry.get("part", []):
            if "content" in p:
                descriptions_nl.append(p["content"])
            for sub in p.get("part", []):
                if "content" in sub:
                    descriptions_nl.append(sub["content"])
    # deduplicate
    descriptions_nl = list(dict.fromkeys(descriptions_nl))

    description = " ".join(descriptions_nl)

    # ------------ LOCATION ------------
    location = None
    room = None
    loc = data.get('current_location', [])

    if loc:
        for item in loc.get("identified_by", []):
        
            # 1. Extract identifier
            if item.get("type") == "Identifier":
                if "content" in item:
                    room = item["content"]
        
            # 2. Extract location name in english
            if item.get("type") == "Name":
                langs = item.get("language", [])
                if any(l.get("id") == en_code for l in langs):
                    parts = item.get("part", [])
                    names = [p.get("content") for p in parts if p.get("content")]
                    location = " ".join(names)
                    
    # ------------ DIMENSION ------------        
    entries = []
    
    for item in data.get("dimension", []):
        if item.get("type") != "Dimension":
            continue
        
        value = item.get("value")
        unit_id = item.get("unit", {}).get("id")
        unit = unit_map.get(unit_id, "")
        
        # get attribute from classified_as
        attr = None
        for c in item.get("classified_as", []):
            a = attr_map.get(c.get("id"))
            if a:
                attr = a
        
        # gather the Dutch annotation text
        annotation = None
        for ref in item.get("referred_to_by", []):
            langs = ref.get("language", [])
            if any(l.get("id") == en_code for l in langs):
                annotation = ref.get("content")
    
        if attr and value and unit:
            entries.append(f"{attr} {value} {unit}" + (f" ({annotation})" if annotation else ""))
            
    dimension_str = " x ".join(entries)

    # ------------ MATERIAL ------------        

    material_code = "http://vocab.getty.edu/aat/300435429"
    
    materials = []
    
    for item in data.get("referred_to_by", []):
        if item.get("type") != "LinguisticObject":
            continue
        
        langs = item.get("language", [])
        if not any(l.get("id") == en_code for l in langs):
            continue
    
        classes = item.get("classified_as", [])
        if not any(c.get("id") == material_code for c in classes):
            continue
    
        content = item.get("content")
        if content:
            materials.append(content)
    
    materials = list(dict.fromkeys(materials))

    
    return {
        "title": title,
        "artist": artist_name,
        "year": year,
        "description": description,
        "location": location,
        "room": room,
        "dimension": dimension_str,
        "material": materials,
        "source": data.get("id"),
    }

def wikidata_search(title):
    """
    Search for a Wikidata item by title.

    :param title: The title to search for.
    :return: A list of search results.
    """
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "language": "en",
        "format": "json",
        "search": title
    }
    # Set a reasonable User-Agent header to identify the bot
    headers = {"User-Agent": "RijksmuseumRAGBot/1.0 (https://example.com; contact@example.com)"}
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    return r.json()["search"]


def wikidata_get(qid):
    """
    Retrieve a Wikidata entity by its ID.

    :param qid: The ID of the entity to retrieve.
    :return: The retrieved entity as a dictionary.
    """
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    headers = {"User-Agent": "RijksmuseumRAGBot/1.0 (https://example.com; contact@example.com)"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data["entities"][qid]


def select_painting(results):
    """
    Select a painting from a list of search results.

    :param results: A list of search results.
    :return: The ID of the selected painting, or None if no painting was found.
    """
    for item in results:
        # Get the ID and entity of the current item
        qid = item["id"]
        entity = wikidata_get(qid)
        claims = entity.get("claims", {})
        
        if "P31" in claims:
            for inst in claims["P31"]:
                if inst["mainsnak"]["datavalue"]["value"]["id"] == "Q3305213": # Wiki code for painting
                    return qid
    
    # If no painting was found, return None
    return None


def wikidata_get_sitelink(qid, lang="en"):
    """
    Retrieve the sitelink of a Wikidata entity in a given language.

    :param qid: The ID of the entity to retrieve.
    :param lang: The language of the sitelink to retrieve. Defaults to "en".
    :return: The sitelink of the entity in the given language.
    """
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    headers = {
        "User-Agent": "RijksmuseumRAGBot/1.0 (https://example.com; contact@example.com)"
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    entity = data["entities"][qid]
    sitelinks = entity["sitelinks"]
    # The language is the key of the sitelink
    return sitelinks[f"{lang}wiki"]["title"]

def select_artist(results):
    """
    Select an artist from a list of search results.

    :param results: A list of search results.
    :return: The ID of the selected artist, or None if no artist was found.
    """
    for item in results:
        qid = item["id"]
        entity = wikidata_get(qid)
        claims = entity.get("claims", {})

        # Check if the current item is an instance of = human (Q5)
        if "P31" in claims:
            for inst in claims["P31"]:
                if inst["mainsnak"]["datavalue"]["value"]["id"] == "Q5":
                    # If the current item is an instance of human, return its ID
                    return qid
    
    # If no artist was found, return None
    return None

def wikipedia_content(title, lang="en"):
    """
    Retrieve the content of a Wikipedia page.

    :param title: The title of the page to retrieve.
    :param lang: The language of the page to retrieve. Defaults to "en".
    :return: The content of the page as a string.
    """
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": True,    # remove HTML
        "format": "json",
        "titles": title
    }
    headers = {
        "User-Agent": "RijksmuseumRAGBot/1.0 (https://example.com; contact@example.com)"
    }
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    data = r.json()
    pages = data["query"]["pages"]
    # Get the first page
    page = next(iter(pages.values()))
    return page.get("extract", "")

def aggregate_data(df, wiki_artwork_content, wiki_artist_bio, rel_artworks):
    """
    Aggregate the data from the Rijksmuseum API and the Wikipedia API.

    :param df: The DataFrame containing the data from the Rijksmuseum API.
    :param wiki_artwork_content: The content of the Wikipedia page of the artwork.
    :param wiki_artist_bio: The content of the Wikipedia page of the artist.
    :param rel_artworks: A list of artworks by the artist.
    :return: A DataFrame containing the aggregated data.
    """
    final_data = df.copy()
    final_data['wiki_artwork'] = wiki_artwork_content
    final_data['wiki_artist'] = wiki_artist_bio
    final_data['artist_artworks'] = rel_artworks
    return final_data

def data_extraction(search_set):
    """
    Extract data for the artworks using the Rijksmuseum API and the Wikipedia API.
    :param search_set: A dictionary containing the artworks that need to be extracted.
    :return: A dictionary containing the extracted data.
    """
    artworks_data = {}
    for creator, titles in search_set.items():
        for title in titles:
            print(f'Scraping info for artwork "{title}" of {creator}')
            
            data = search_portraits(title=title, creator=creator)
            rijks_artwork_id = data["orderedItems"][0]['id']
            actual_id = re.search(r'/(\d+)(?:\?|$)', rijks_artwork_id).group(1)
    
            extracted_info = requests.get(rijks_artwork_id, headers={"Accept": "application/ld+json"}).json()
            
            extracted_data = parse_artwork_details(extracted_info)
            extracted_data['artist'] = extracted_data['artist'].replace("painter: ", "").strip() # cleaning

            # find all the other artworks from the artist
            rel_artworks = []
            data_artist = search_portraits(creator=creator)
            if len(data_artist['orderedItems']) > 0:
                for items in data_artist['orderedItems']:
                    if rijks_artwork_id != items['id']:
                        rel_art_id = items['id']
                        rel_art_extracted_info = requests.get(rel_art_id, headers={"Accept": "application/ld+json"}).json()
                        rel_art_extracted_data = parse_artwork_details(rel_art_extracted_info)
                        rel_art_extracted_data['artist'] = rel_art_extracted_data['artist'].replace("painter: ", "").strip() # cleaning
                        rel_art_extracted_data = {k: rel_art_extracted_data[k] for k in ['title', 'room', 'location', 'artist']}
                        if rel_art_extracted_data['title'] is not None:
                            rel_artworks.append(rel_art_extracted_data)
            if (title != 'Self-Portrait') and (creator != 'Van Gogh'): # edge case cause self portrait has multiple paintings not a specific one
                results = wikidata_search(title)
                qid = select_painting(results)
                wiki_title = wikidata_get_sitelink(qid)
            else:
                wiki_title = 'https://en.wikipedia.org/wiki/Portraits_of_Vincent_van_Gogh' # retrieve info of the whole category
            wiki_artwork_content = wikipedia_content(wiki_title, lang="en")

            # wiki for artist
            artist_results = wikidata_search(creator)
            artist_qid = select_artist(artist_results)
            artist_wiki_title = wikidata_get_sitelink(artist_qid, lang="en")
            wiki_artist_bio = wikipedia_content(artist_wiki_title)
            painting_data = aggregate_data(extracted_data, wiki_artwork_content, wiki_artist_bio, rel_artworks)
            
            artworks_data[actual_id] = painting_data
    return artworks_data

def save_json(data, folder_path, save_path):
    """
    Save the given data to the file path.
    Args:
        data (dict): The data to be saved.
        folder_path (str): The path to the folder to save the data in.
        save_path (Path): The path to the JSON file to save the data in.

    """
    data_dir = Path(folder_path)
    data_dir.mkdir(exist_ok=True)
    with open(save_path, "w", encoding="utf-8") as f:
        # Save the data to the JSON file with indentation
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    all_data = data_extraction(search_set)
    save_json(all_data, folder_path, extracted_data_path)
    logger.info('Success, data saved into {}'.format(extracted_data_path))