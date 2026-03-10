# Chatbot for the Rijksmuseum

This project is part of the Data Systems Project at the University of Amsterdam and focuses on designing and evaluating a chatbot that enables users to explore artworks of the Rijksmuseum.

To run the chatbot: 

* clone the project
```bash
cd Chatbot-for-the-Rijksmuseum
```
* Install requirements
```bash
pip install -r requirements.txt
```


* Add your .env file

* Retrieve museum and Wikipedia data for the selected artists (found in src/config.py):
```bash
python -m src.data_extraction
```
* Then build the Chroma vector database:
```bash
python -m src.build_chroma_db
```
For the style imitation of Van Gogh's artworks in the model responses: 
* Download xml data from van Gogh letters via here: https://vangoghletters.org/vg/vangoghxml.zip. Place it in Data/data_vangogh/.
```bash
python -m src.xml_parser
```
 and select 1 for the Dutch/French original version, or 2 for the translated English version.

* Generate embeddings for predefined artistic questions:
```bash
python -m src.questions_embeddings
```
* Test the question-answering pipeline: (Optional)
```bash
python -m src.question_answering
```
To launch the web interface:
```bash
uvicorn app:app --reload
```

You can also run the app using Docker:

Build image

```docker build -t rijksmuseum-app . ```


Run container

```
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="your key" \
  rijksmuseum-app
```

The app will be available at http://localhost:8000
