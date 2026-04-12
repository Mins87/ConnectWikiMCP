# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some MarkItDown sub-dependencies like Magika)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY src/ /app/src/

# Create a default wiki directory (should be mapped as a volume)
RUN mkdir -p /app/wiki

# Define environment variables for internal usage
ENV WIKI_ROOT_PATH=/app/wiki

# Command to run the MCP server
# Use -i flag when running this container for STDIO communication
CMD ["python", "src/server.py"]
