#!/bin/bash
set -e -o pipefail

PORT=3098

fail() {
    echo "start.sh: ERROR: $1"
    echo "start.sh: Exiting in 20 seconds (kept alive so this message reaches the worker log)..."
    sleep 20
    exit 1
}

cleanup() {
    echo "start.sh: Cleaning up..."
    pkill -P $$ || true
    exit 0
}

CACHED_LLAMA_ARGS=""

# Return 0 if cached model path resolves, else return 1 (no exit here).
find_cached_path() {
    local model_path
    model_path="$(python ./find_cached.py "$LLAMA_CACHED_MODEL" "$LLAMA_CACHED_GGUF_PATH" 2>/dev/null)" || return 1
    [ -n "$model_path" ] || return 1
    CACHED_LLAMA_ARGS="-m $model_path"
    return 0
}

# Map HF_TOKEN (template field) to the env var huggingface_hub expects.
if [ -n "${HF_TOKEN:-}" ] && [ -z "${HUGGINGFACE_HUB_TOKEN:-}" ]; then
    export HUGGINGFACE_HUB_TOKEN="$HF_TOKEN"
fi

# Put Hugging Face caches on the mounted volume for persistence.
if [ -n "${HF_HOME:-}" ]; then
    unset HUGGINGFACE_HUB_CACHE
fi

# Prefer cache if configured; fall back to HF download if not found.
if [ -n "$LLAMA_CACHED_MODEL" ]; then
    echo "start.sh: Model caching is enabled. Resolving cached model path..."
    if find_cached_path; then
        echo "start.sh: Using cached model: $CACHED_LLAMA_ARGS"
        # Cache hit: prevent llama-server from downloading.
        unset LLAMA_ARG_HF_REPO LLAMA_ARG_HF_FILE LLAMA_ARG_MODEL
    else
        echo "start.sh: Cache miss; falling back to Hugging Face download."
        CACHED_LLAMA_ARGS=""
        # Keep LLAMA_ARG_HF_REPO / LLAMA_ARG_HF_FILE so llama-server can download.
    fi
fi

# A .gguf filename pasted into the Quantization field is a common mistake.
if [[ "$LLAMA_HF_QUANT" == *.gguf ]]; then
    echo "start.sh: LLAMA_HF_QUANT looks like a filename; using it as LLAMA_ARG_HF_FILE instead."
    export LLAMA_ARG_HF_FILE="${LLAMA_ARG_HF_FILE:-$LLAMA_HF_QUANT}"
    LLAMA_HF_QUANT=""
fi

# Combine repo + quant tag when applicable.
if [ -n "$LLAMA_HF_QUANT" ] && [ -n "$LLAMA_ARG_HF_REPO" ] \
    && [[ "$LLAMA_ARG_HF_REPO" != *:* ]] && [ -z "$LLAMA_ARG_HF_FILE" ]; then
    export LLAMA_ARG_HF_REPO="${LLAMA_ARG_HF_REPO}:${LLAMA_HF_QUANT}"
    echo "start.sh: Using model: $LLAMA_ARG_HF_REPO"
fi

# Require some model source to be configured.
if [ -z "$CACHED_LLAMA_ARGS" ] && [ -z "$LLAMA_ARG_HF_REPO" ] && [ -z "$LLAMA_ARG_MODEL" ] \
    && [[ "$LLAMA_SERVER_CMD_ARGS" != *"-hf"* ]] && [[ "$LLAMA_SERVER_CMD_ARGS" != *"-m "* ]]; then
    fail "No model configured. Set LLAMA_ARG_HF_REPO (the Model field in the template), or configure model caching with LLAMA_CACHED_MODEL and LLAMA_CACHED_GGUF_PATH."
fi

# Enforce worker port.
if [[ "$LLAMA_SERVER_CMD_ARGS" == *"--port"* ]]; then
    fail "You must not define --port in LLAMA_SERVER_CMD_ARGS, as port $PORT is required."
fi

trap cleanup SIGINT SIGTERM

echo "start.sh: Stopping existing llama-server instances (if any)..."
pkill llama-server 2>/dev/null || echo "start.sh: No llama-server running"

echo "start.sh: Running /app/llama-server $CACHED_LLAMA_ARGS $LLAMA_SERVER_CMD_ARGS --port $PORT"

touch llama.server.log

LD_LIBRARY_PATH=/app /app/llama-server $CACHED_LLAMA_ARGS $LLAMA_SERVER_CMD_ARGS --port $PORT 2>&1 | tee llama.server.log &

LLAMA_SERVER_PID=$!

echo "start.sh: Waiting for llama-server to become healthy (downloading/loading the model can take a while)..."

until curl -sf "http://127.0.0.1:${PORT}/health" > /dev/null 2>&1; do
    if ! kill -0 "$LLAMA_SERVER_PID" 2>/dev/null; then
        echo "start.sh: llama-server exited unexpectedly. Last log lines:"
        tail -n 40 llama.server.log
        fail "llama-server exited during startup (see log lines above for the reason)."
    fi
    sleep 1
done

echo "start.sh: llama-server is up and running, delegating to the handler script."
python -u handler.py $1
