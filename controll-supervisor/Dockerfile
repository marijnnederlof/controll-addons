ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python and dependencies
RUN apk add --no-cache python3 py3-pip py3-aiohttp py3-yaml nmap

# Copy application
COPY run.py /
COPY rootfs /

# Make executable
RUN chmod a+x /run.py

CMD [ "/run.py" ]
