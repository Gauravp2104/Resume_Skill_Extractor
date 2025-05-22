FROM python:3.9-slim

WORKDIR /app

# ENV PYTHONPATH="${PYTHONPATH}:/app"

RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir /safe_copy && \
    cp -r . /safe_copy && \
    chmod -R 755 /safe_copy

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
