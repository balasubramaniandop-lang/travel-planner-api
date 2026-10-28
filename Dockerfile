FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose port (Render uses $PORT env var)
EXPOSE 8000

# Start server
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
