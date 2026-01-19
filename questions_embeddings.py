from build_chroma_db import embed
from config import predefined_questions, pred_embeddings_path
import os
import numpy as np
from numpy.linalg import norm
from dotenv import load_dotenv
from openai import OpenAI
import json
from loguru import logger

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_predefined_embeddings(predefined_questions, pred_embeddings_path):
    """
    Generate a dictionary with predefined questions and their corresponding corresponding embeddings.

    Parameters
    ----------
    predefined_questions : dict
        A dictionary with art_id as key and a list of predefined questions as value.
    -------
    """
    logger.info(f'Generating embeddings...')
    pred_questions_embeddings = {}
    for art_id, questions in predefined_questions.items():
        embeddings = [embed(q) for q in questions]   
        pred_questions_embeddings[art_id] = {
            "questions": questions,
            "embeddings": np.array(embeddings, dtype=np.float32)
        }
    for k, v in pred_questions_embeddings.items():
        v["embeddings"] = v["embeddings"].tolist()


    # save embeddings to json
    with open(pred_embeddings_path , "w", encoding="utf-8") as f:
        json.dump(pred_questions_embeddings, f, ensure_ascii=False, indent=2) 
        logger.info('Embeddings saved to {}'.format(pred_embeddings_path))

def retrieve_similar_questions(
    query,
    art_id,
    pred_questions_embeddings,
    top_k=6,
    is_predefined=False
):
    """
    Retrieve the top k similar predefined questions based on the query.

    Parameters
    ----------
    query : str/integer
        Either the index of the predefined question, or the question of the user to be embedded
    art_id : str
        The art_id of the predefined questions
    pred_questions_embeddings : dict
        embeddings of predefined questions
    top_k : int, optional
        The number of similar predefined questions to retrieve. default is 6
    is_predefined : bool, optional
        Whether the user selected a predefined question or not
        Default is False
    ----------
    """
    questions = pred_questions_embeddings[art_id]["questions"]
    emb = np.array(pred_questions_embeddings[art_id]["embeddings"], dtype=float)

    # embed or get predefined vector
    if is_predefined:
        # query is an index of a predefined question
        q_vec = emb[query]  
        q_vec = emb[query]  # query = index
    else:
        # query is a string to embed
        q_vec = embed(query)
        q_vec = q_vec / norm(q_vec)

    # normalize embeddings
    emb_norm = emb / norm(emb, axis=1, keepdims=True)

    # cosine similarity
    sims = emb_norm @ q_vec

    # sort
    if is_predefined:
        best = sims.argsort()[::-1][1:top_k+1]  # Do not return the same predefined question but all the subsequent ones
    else:
        best = sims.argsort()[::-1][:top_k]  # return the top k similar predefined questions

    results = [
        {
            "index": int(i),
            "question": questions[i],
            "score": float(sims[i])
        }
        for i in best
    ]
    return results

if __name__ == "__main__":
    generate_predefined_embeddings(predefined_questions, pred_embeddings_path)