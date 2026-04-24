FROM python:3.12-bookworm

ARG SYFT_VERSION=latest
ARG GRYPE_VERSION=latest
ARG CODEQL_VERSION=latest

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/codeql:${PATH}"
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        nodejs \
        npm \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    if [ "${SYFT_VERSION}" = "latest" ]; then \
        curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
            | sh -s -- -b /usr/local/bin; \
    else \
        curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
            | sh -s -- -b /usr/local/bin "${SYFT_VERSION}"; \
    fi; \
    if [ "${GRYPE_VERSION}" = "latest" ]; then \
        curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
            | sh -s -- -b /usr/local/bin; \
    else \
        curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
            | sh -s -- -b /usr/local/bin "${GRYPE_VERSION}"; \
    fi

RUN set -eux; \
    if [ "${CODEQL_VERSION}" = "latest" ]; then \
        CODEQL_URL="$(curl -sSfL https://api.github.com/repos/github/codeql-action/releases/latest \
            | jq -r '.assets[] | select(.name == "codeql-bundle-linux64.tar.gz") | .browser_download_url')"; \
    else \
        CODEQL_URL="https://github.com/github/codeql-action/releases/download/${CODEQL_VERSION}/codeql-bundle-linux64.tar.gz"; \
    fi; \
    test -n "${CODEQL_URL}"; \
    curl -sSfL "${CODEQL_URL}" -o /tmp/codeql-bundle-linux64.tar.gz; \
    tar -xzf /tmp/codeql-bundle-linux64.tar.gz -C /opt; \
    rm /tmp/codeql-bundle-linux64.tar.gz; \
    ln -sf /opt/codeql/codeql /usr/local/bin/codeql; \
    codeql version

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY scripts/check_prereqs.py /tmp/check_prereqs.py
RUN python /tmp/check_prereqs.py

COPY . /workspace

CMD ["bash", "scripts/run_all.sh"]
