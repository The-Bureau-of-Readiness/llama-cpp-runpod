# Official llama.cpp server image. The digest pin is managed automatically by
# .github/workflows/latest-llamacpp.yml, which follows the floating
# server-cuda tag and cuts a release named after the llama.cpp build number.
FROM ghcr.io/ggml-org/llama.cpp:server-cuda@sha256:31b39eacce2bab5fde9286ec3980ed5548a3987644e94da0d0c2092f93313538

ENV PYTHONUNBUFFERED=1
# Optional default: make HF caching land on the Runpod mounted volume.
# You can omit this if you prefer to set HF_HOME in hub.json only.
ENV HF_HOME=/runpod-volume/huggingface-cache

WORKDIR /

RUN apt-get update --yes --quiet && DEBIAN_FRONTEND=noninteractive apt-get install --yes --quiet --no-install-recommends \
    software-properties-common \
    gpg-agent \
    build-essential apt-utils \
    && apt-get install --reinstall ca-certificates \
    && add-apt-repository --yes ppa:deadsnakes/ppa && apt update --yes --quiet \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --quiet --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3.11-lib2to3 \
    python3.11-gdbm \
    python3.11-tk \
    bash \
    curl && \
    ln -sf /usr/bin/python3.11 /usr/bin/python && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /work

ADD ./src /work
COPY handler.py /work/handler.py

RUN pip install -r ./requirements.txt && chmod +x /work/start.sh

ENTRYPOINT ["/work/start.sh"]

