FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy app entrypoint & config
COPY app.py config.py ./

# Copy Data
COPY Data ./Data

# Copy Database
COPY db_rijksmuseum ./db_rijksmuseum

# Copy source code
COPY src ./src

EXPOSE 8000
ENV PORT=8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
