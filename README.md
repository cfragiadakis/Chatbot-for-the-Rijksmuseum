* pip install -r requirements.txt
* Add your .env file
* run python -m src.data_extraction to retrieve data from Rijksmuseum and Wikipedia API.
* run python -m src.build_chroma_db to build chroma db of extracted data.

* Download xml data from van Gogh letters via here: https://vangoghletters.org/vg/vangoghxml.zip. Place it in Data/data_vangogh/.
* run python -m src.xml_parser and select 2 for English version of Van Gogh's letters to imitate style.
* run python -m src.questions_embeddings
* run python -m src.question_answering to test the chatbot answers imitating artist's tone.
* To run the webserver, use uvicorn app:app --reload
