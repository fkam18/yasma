FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    exiftool \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project fresh
COPY . .

# Delete any bytecode that may have been copied from the host
RUN find /app -type d -name '__pycache__' -exec rm -rf {} + ; \
    find /app -type f -name '*.pyc' -delete

EXPOSE 3333
CMD ["uvicorn", "yasma.main:app", "--host", "0.0.0.0", "--port", "3333"]
