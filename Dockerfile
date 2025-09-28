# =========================
# ======== BUILDER ========
# =========================
FROM ubuntu:24.04 AS builder
SHELL ["/bin/bash","-o","pipefail","-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    LANG=C.UTF-8 \
    HOME=/root

WORKDIR /data/www

# Base build toolchain + libs needed to build any stragglers
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl wget gnupg \
      git make build-essential \
      tzdata unzip xz-utils pkg-config \
      libffi-dev libssl-dev zlib1g-dev \
      libbz2-dev libreadline-dev libsqlite3-dev \
      libncursesw5-dev libgdbm-dev libnss3-dev \
      liblzma-dev tk-dev \
 && rm -rf /var/lib/apt/lists/*

# Python 3.8 from deadsnakes (matches the app)
RUN set -eux; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xBA6932366A755776" \
      | gpg --dearmor > /etc/apt/keyrings/deadsnakes.gpg; \
    echo "deb [signed-by=/etc/apt/keyrings/deadsnakes.gpg] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu noble main" \
      > /etc/apt/sources.list.d/deadsnakes-ppa.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      python3.8 python3.8-dev python3.8-venv python3.8-distutils python3-lib2to3; \
    rm -rf /var/lib/apt/lists/*

# AWS CLI v2 (you had this in the working image history)
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip \
 && unzip /tmp/awscliv2.zip -d /tmp \
 && /tmp/aws/install \
 && rm -rf /tmp/aws /tmp/awscliv2.zip

# Legacy Node (webpack pipeline for master_docker)
ENV NODE_VERSION=v14.21.3 \
    NODE_DIST=node-v14.21.3-linux-x64 \
    NODE_HOME=/usr/local/node14 \
    npm_config_fund=false \
    npm_config_audit=false \
    npm_config_unsafe_perm=true
RUN curl -fsSL "https://nodejs.org/dist/${NODE_VERSION}/${NODE_DIST}.tar.xz" -o /tmp/node.tar.xz \
 && mkdir -p "${NODE_HOME}" \
 && tar -xJf /tmp/node.tar.xz -C "${NODE_HOME}" --strip-components=1 \
 && ln -sf "${NODE_HOME}/bin/node" /usr/local/bin/node \
 && ln -sf "${NODE_HOME}/bin/npm"  /usr/local/bin/npm \
 && ln -sf "${NODE_HOME}/bin/npx"  /usr/local/bin/npx \
 && rm -f /tmp/node.tar.xz

# Clone the backend
RUN git clone https://github.com/yeastgenome/SGDBackend-Nex2.git
WORKDIR /data/www/SGDBackend-Nex2
RUN git checkout master_docker \
 && git config --global url."https://".insteadOf git://

# Python venv inside the repo (like the working one)
RUN python3.8 -m venv /data/www/SGDBackend-Nex2/venv
ENV VENV=/data/www/SGDBackend-Nex2/venv
ENV PATH="${VENV}/bin:/usr/local/node14/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
# Keep these for legacy packages (use_2to3, etc.)
ENV PIP_NO_BUILD_ISOLATION=1 \
    SETUPTOOLS_USE_DISTUTILS=local \
    SETUPTOOLS_ENABLE_FEATURES=legacy-editable
# IMPORTANT: do NOT globally disable PEP 517; PyYAML needs its backend
ENV PIP_USE_PEP517=

# Legacy build tools (match working image)
RUN python -m pip install --no-cache-dir \
      "pip<25" "setuptools==57.5.0" "wheel==0.37.0" "Cython<3"

# --- Fix PyYAML / PEP 517 issue ---
# Preinstall PyYAML from wheel so pip won't try to build it with PEP 517 bridge
# Use the version your reqs finally resolve to; 6.0.1 has cp38 manylinux wheels
RUN python -m pip install --no-cache-dir --only-binary=:all: "PyYAML==6.0.1" || \
    python -m pip install --no-cache-dir --only-binary=:all: "PyYAML==6.0"

# Install requirements FIRST (this was the huge layer in 20250913)
# --prefer-binary keeps us on wheels (fast & close to old image)
RUN python -m pip install --no-cache-dir --prefer-binary -r requirements.txt

# Editable install to match 20250913 behavior
RUN python -m pip install -e . --no-build-isolation --config-settings editable_mode=compat

# Build the legacy webpack bundle (don’t let lockfile drift fail the layer)
RUN npm --version \
 && ( npm ci --legacy-peer-deps || npm install --legacy-peer-deps ) \
 && ( npm run build || true ) \
 && npm cache clean --force || true

# Keep Makefile build step (non-fatal)
RUN sed -i -E 's|^([[:space:]]*)python([0-9\.]*)?[[:space:]]+setup\.py[[:space:]]+develop.*|\1@true # skipped: handled in Dockerfile|g' Makefile || true \
 && sed -i -E 's|^([[:space:]]*)\$\((PYTHON|python)\)[[:space:]]+setup\.py[[:space:]]+develop.*|\1@true # skipped: handled in Dockerfile|g' Makefile || true \
 && ( make build || true )

# Create runtime dirs & perms expected by your scripts
RUN mkdir -p /data/www/logs /data/www/tmp \
 && chmod 755 /data/www/SGDBackend-Nex2/system_config/cron/* || true

# Trim caches in builder (doesn't affect runtime size but keeps this stage tidy)
RUN python -m pip cache purge || true \
 && rm -rf ~/.cache /root/.cache node_modules || true


# =========================
# ======== RUNTIME ========
# =========================
FROM ubuntu:24.04 AS runtime
SHELL ["/bin/bash","-o","pipefail","-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    LANG=C.UTF-8 \
    INI_FILE=/data/www/SGDBackend-Nex2/development.ini

WORKDIR /data/www

# Minimal runtime libs used by your wheels (matches your “bigger” working image)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl tzdata unzip gnupg \
      # Python runtime deps
      libffi8 libssl3 zlib1g libstdc++6 libgcc-s1 \
      # lxml / xml
      libxml2 libxslt1.1 \
      # psycopg2-binary
      libpq5 \
      # numpy/pandas/biopython/BLAS bits
      libgfortran5 libopenblas0 libgomp1 \
      # imaging stack used by some deps
      libjpeg-turbo8 libpng16-16 libtiff6 libfreetype6 \
      # others seen present in the larger image
      libicu74 libkrb5-3 \
 && rm -rf /var/lib/apt/lists/*

# Python 3.8 interpreter for the venv
RUN set -eux; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xBA6932366A755776" \
      | gpg --dearmor > /etc/apt/keyrings/deadsnakes.gpg; \
    echo "deb [signed-by=/etc/apt/keyrings/deadsnakes.gpg] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu noble main" \
      > /etc/apt/sources.list.d/deadsnakes-ppa.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends python3.8 python3.8-distutils; \
    rm -rf /var/lib/apt/lists/*

# Postfix was present in the old working image history (small, but keeps parity)
RUN apt-get update \
 && apt-get install -y --no-install-recommends postfix \
 && rm -rf /var/lib/apt/lists/*

# AWS CLI v2 (present in the big image)
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip \
 && unzip /tmp/awscliv2.zip -d /tmp \
 && /tmp/aws/install \
 && rm -rf /tmp/aws /tmp/awscliv2.zip

# Bring over the built app (repo + venv + compiled assets)
COPY --from=builder /data/www/SGDBackend-Nex2 /data/www/SGDBackend-Nex2
COPY --from=builder /data/www/SGDBackend-Nex2/venv /data/www/SGDBackend-Nex2/venv

# Runtime dirs & perms
RUN mkdir -p /data/www/logs /data/www/tmp \
 && chmod 755 /data/www/SGDBackend-Nex2/system_config/cron/* || true

# Use the venv by default
ENV PATH="/data/www/SGDBackend-Nex2/venv/bin:${PATH}"

# Network binding: ensure it listens on 0.0.0.0 in Fargate
EXPOSE 6543
CMD ["bash","-lc","pserve ${INI_FILE} http_host=0.0.0.0"]
