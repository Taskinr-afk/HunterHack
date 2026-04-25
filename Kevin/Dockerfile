FROM python:3.13-slim

WORKDIR /app

# Install system deps required by XGBoost (libomp) and scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY kevin/cortex/requirements.txt cortex-requirements.txt
COPY kevin/api/requirements.txt api-requirements.txt
RUN pip install --no-cache-dir -r cortex-requirements.txt -r api-requirements.txt

# Copy source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "kevin.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
