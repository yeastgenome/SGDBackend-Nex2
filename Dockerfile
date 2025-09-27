# =========================
# ======== BUILDER ========
# =========================
FROM ubuntu:24.04 AS builder
SHELL ["/bin/bash","-o","pipefail","-c"]

ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC LANG=C.UTF-8

WORKDIR /data/www

# Base build toolchain + libs
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl wget gnupg \
      git make build-essential \
      tzdata unzip xz-utils \
      libffi-dev libssl-dev zlib1g-dev \
      pkg-config \
 && rm -rf /var/lib/apt/lists/*

# Deadsnakes PPA (Python 3.8 toolchain for legacy deps)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends gnupg; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xBA6932366A755776" \
      | gpg --dearmor > /etc/apt/keyrings/deadsnakes.gpg; \
    echo "deb [signed-by=/etc/apt/keyrings/deadsnakes.gpg] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu noble main" \
      > /etc/apt/sources.list.d/deadsnakes-ppa.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      python3.8 python3.8-dev python3.8-venv python3.8-distutils python3-lib2to3 \
    ; \
    rm -rf /var/lib/apt/lists/*

# Clone app
RUN git clone https://github.com/yeastgenome/SGDBackend-Nex2.git
WORKDIR /data/www/SGDBackend-Nex2
RUN git checkout master_docker \
 && git config --global url."https://".insteadOf git://

# Python venv (builder)
RUN python3.8 -m venv /data/www/SGDBackend-Nex2/venv
ENV PATH="/data/www/SGDBackend-Nex2/venv/bin:${PATH}" \
    PIP_NO_BUILD_ISOLATION=1 \
    SETUPTOOLS_USE_DISTUTILS=local

# Pin legacy build tooling for old packages (anyjson/use_2to3, primer3-py/Cython)
RUN python -m pip install --no-cache-dir \
      "pip<25" "setuptools==57.5.0" "wheel==0.37.0" "Cython<3"

# Python deps and **non-editable** install of your app
RUN python -m pip install --no-cache-dir -r requirements.txt \
 && python -m pip install --no-cache-dir .

# --- Node for webpack build (backend expects very old webpack) ---
ENV NODE_VERSION=v14.21.3 \
    NODE_DIST=node-v14.21.3-linux-x64 \
    NODE_HOME=/usr/local/node14 \
    npm_config_fund=false npm_config_audit=false npm_config_unsafe_perm=true
RUN curl -fsSL https://nodejs.org/dist/${NODE_VERSION}/${NODE_DIST}.tar.xz -o /tmp/node.tar.xz \
 && mkdir -p ${NODE_HOME} \
 && tar -xJf /tmp/node.tar.xz -C ${NODE_HOME} --strip-components=1 \
 && ln -sf ${NODE_HOME}/bin/{node,npm,npx} /usr/local/bin/ \
 && rm -f /tmp/node.tar.xz

# Build JS bundle (don’t let a flaky npm step fail the whole build)
RUN if [ -f package-lock.json ]; then npm ci --legacy-peer-deps; else npm install --legacy-peer-deps; fi \
 && (npm run build || true)

# Optionally run your Makefile build if it does extra steps (won’t fail the layer)
RUN (make build || true)

# Clean caches
RUN python -m pip cache purge || true \
 && rm -rf ~/.cache /root/.cache node_modules || true

# Ensure runtime dirs exist and perms set
RUN mkdir -p /data/www/logs /data/www/tmp \
 && chmod 755 system_config/cron/* || true


# =========================
# ======== RUNTIME ========
# =========================
FROM ubuntu:24.04 AS runtime
SHELL ["/bin/bash","-o","pipefail","-c"]

ENV DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC LANG=C.UTF-8 \
    INI_FILE=/data/www/SGDBackend-Nex2/development.ini

WORKDIR /data/www

# Minimal runtime libs + Python 3.8
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl tzdata unzip gnupg \
      libffi8 libssl3 \
 && rm -rf /var/lib/apt/lists/*
RUN set -eux; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xBA6932366A755776" \
      | gpg --dearmor > /etc/apt/keyrings/deadsnakes.gpg; \
    echo "deb [signed-by=/etc/apt/keyrings/deadsnakes.gpg] http://ppa.launchpad.net/deadsnakes/ppa/ubuntu noble main" \
      > /etc/apt/sources.list.d/deadsnakes-ppa.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends python3.8 python3.8-distutils \
    ; \
    rm -rf /var/lib/apt/lists/*

# (Optional) AWS CLI v2 if you rely on it at runtime
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip \
 && unzip /tmp/awscliv2.zip -d /tmp \
 && /tmp/aws/install \
 && rm -rf /tmp/aws /tmp/awscliv2.zip

# Bring over the built venv and the full repo (with built assets)
COPY --from=builder /data/www/SGDBackend-Nex2/venv /data/www/SGDBackend-Nex2/venv
COPY --from=builder /data/www/SGDBackend-Nex2 /data/www/SGDBackend-Nex2

# Runtime dirs & perms
RUN mkdir -p /data/www/logs /data/www/tmp \
 && chmod 755 /data/www/SGDBackend-Nex2/system_config/cron/* || true

# Use venv python/pip by default
ENV PATH="/data/www/SGDBackend-Nex2/venv/bin:${PATH}"

EXPOSE 6543

# IMPORTANT: no --reload in containers (avoids hupper worker/healthcheck races)
CMD ["bash","-lc","pserve ${INI_FILE}"]
