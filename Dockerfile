FROM postgres:15

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-requests \
    python3-pandas \
    python3-psycopg2 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

ENV POSTGRES_DB=postgres
ENV POSTGRES_USER=postgres
ENV POSTGRES_HOST_AUTH_METHOD=trust

COPY schema.sql /docker-entrypoint-initdb.d/
COPY import_data.py /import_data.py
COPY postgrest.conf /postgrest.conf


RUN apt-get update && apt-get install -y postgresql-client curl

RUN curl -L https://github.com/PostgREST/postgrest/releases/download/v12.2.8/postgrest-v12.2.8-linux-static-x86-64.tar.xz | \
    tar -xJ -C /usr/local/bin \
    && chmod +x /usr/local/bin/postgrest

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
