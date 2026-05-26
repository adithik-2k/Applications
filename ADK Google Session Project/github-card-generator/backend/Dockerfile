FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies
COPY requirements.txt .
# Adding google-adk explicitly as it was installed manually during dev
RUN echo "google-adk" >> requirements.txt
RUN uv pip install --no-cache -r requirements.txt --system

# Copy source
COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
