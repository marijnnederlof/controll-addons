ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-aiohttp \
    py3-yaml \
    nmap \
    netcat-openbsd

# Copy application
COPY run.py /run.py

# Make executable
RUN chmod a+x /run.py

CMD [ "python3", "/run.py" ]
