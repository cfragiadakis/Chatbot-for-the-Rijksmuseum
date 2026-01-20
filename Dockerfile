# 1️⃣ Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2️⃣ Set working directory inside the container
WORKDIR /app

# 3️⃣ Copy requirements first to leverage caching
COPY requirements.txt .

# 4️⃣ Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 5️⃣ Copy all needed files and folders
COPY Data ./Data
COPY db_rijksmuseum ./db_rijksmuseum
COPY configs ./configs
COPY dsp-fastapi ./dsp-fastapi
COPY static ./static
COPY templates ./templates

COPY app.py .
COPY question_answering.py .
COPY questions_embeddings.py .
COPY museum_api.py .
COPY style_loader.py .
COPY config.py .
COPY build_chroma_db.py .
COPY data_extraction.py .

# 6️⃣ Expose port (Railway will map $PORT to this)
EXPOSE 8000

# 7️⃣ Set environment variables default (can override on Railway)
ENV PORT=8000

# 8️⃣ Start the app
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
