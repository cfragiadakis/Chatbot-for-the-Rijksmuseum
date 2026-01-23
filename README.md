### Chatbot for the Rijksmuseum

## Installation

```bash
pip install -r requirements.txt

* Add your .env file

Retrieve museum and Wikipedia data for the selected artists (found in src/config.py):
* python -m src.data_extraction to retrieve data.

Then build the Chroma vector database:
* python -m src.build_chroma_db to build chroma db of extracted data.

For the style imitation of Van Gogh's artworks in the model responses: 
* Download xml data from van Gogh letters via here: https://vangoghletters.org/vg/vangoghxml.zip. Place it in Data/data_vangogh/.
* python -m src.xml_parser and select 1 for the Dutch/French original version, or 2 for the translated English version.

Generate embeddings for predefined artistic questions:
* python -m src.questions_embeddings

Test the question-answering pipeline:
* python -m src.question_answering

To launch the web interface:
* uvicorn app:app --reload
