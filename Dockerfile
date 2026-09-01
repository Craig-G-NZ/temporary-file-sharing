FROM python:3.12-slim

# Set working directory
WORKDIR /

# Copy hashed lockfile first to leverage Docker cache
COPY requirements.lock.txt .

# Install the exact resolved wheels (hashes pin every transitive dependency)
RUN pip install --no-cache-dir --require-hashes --only-binary :all: -r requirements.lock.txt

# Copy application code and prepare runtime directories as a non-root user
COPY ./app ./app
RUN mkdir -p /app/uploads /app/data /app/logs \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "600", "app.run:app"]
