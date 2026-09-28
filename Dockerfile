FROM python:3.12-slim-bookworm

# 1. Install necessary Linux system dependencies for Odoo
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    wkhtmltopdf \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir psycopg2-binary

# 3. Copy project files into container
COPY . .

# 4. Expose the port
EXPOSE 8069

# 5. Start Odoo using smart initialization entrypoint
CMD ["python3", "entrypoint.py"]
