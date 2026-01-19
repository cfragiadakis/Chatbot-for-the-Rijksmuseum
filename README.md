* pip install -r requirements.txt
* Append your .env file
* run python data_extraction.py to retrieve data from Rijksmuseum and Wikipedia API.
* run python build_chroma_db.py to build chroma db of extracted data.

* Download xml data from van Gogh letters via here: https://vangoghletters.org/vg/vangoghxml.zip
Place it in Data/data_vangogh/.
* run python xml_parser.py and select 2 for English version of Van Gogh's letters to imitate style.
* run python questions_embeddings.py
* run python .\question_answering.py to test the chatbot answers imitating artist's tone.
* To run the webserver, use uvicorn app:app --reload
