FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY Backend/cortex/requirements.txt cortex-requirements.txt
COPY Backend/app/requirements.txt    api-requirements.txt
RUN pip install --no-cache-dir -r cortex-requirements.txt -r api-requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "Backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
