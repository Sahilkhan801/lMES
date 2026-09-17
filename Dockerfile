FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose port (Render sets PORT env, but exposing 10000 is standard)
EXPOSE 10000

# Set environment variable for path finding of tesseract
ENV TESSERACT_CMD=/usr/bin/tesseract

# Run the app with gunicorn
CMD ["sh", "-c", "gunicorn --timeout 120 -b 0.0.0.0:${PORT:-10000} app:app"]
