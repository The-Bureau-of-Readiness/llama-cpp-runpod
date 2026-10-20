[![Runpod](https://api.runpod.io/badge/The-Bureau-of-Readiness/qwen3.8-gguf_vision-256k-1m_serverless-llama-cpp)](https://console.runpod.io/hub/listing/The-Bureau-of-Readiness/qwen3.8-gguf_vision-256k-1m_serverless-llama-cpp)
[![Release](https://img.shields.io/github/v/release/The-Bureau-of-Readiness/qwen3.8-gguf_vision-256k-1m_serverless-llama-cpp?display_name=tag&sort=semver)](https://github.com/The-Bureau-of-Readiness/qwen3.8-gguf_vision-256k-1m_serverless-llama-cpp/releases)

<p align="center">
    <img src="https://raw.githubusercontent.com/ggml-org/llama.cpp/master/media/llama1-icon-transparent.png" alt="llama.cpp logo" width="128">
</p>

# Serverless 256K–1M Qwen3p8 / Qwen3.8-Flash-Next-IQ3_S + Vision (optional Coder variant, llama.cpp, auto model cache)

Serverless worker adapted from `llama-cpp-runpod` for Qwen3.8/Qwen3p8 Flash-Next (IQ3_S), with a vision-enabled 256K–1M token long context. Includes presets for the base model and an optional Coder variant. You can also point it at other trimmed GGUF repos by changing `LLAMA_ARG_HF_REPO` and `MMPROJ_HF_FILE`.

This worker runs [llama.cpp](https://github.com/ggml-org/llama.cpp)’s `llama-server` and exposes an OpenAI-compatible API:

- `/v1/models`
- `/v1/chat/completions`
- `/v1/completions`

Streaming is supported.

The Docker image is built on the official `ghcr.io/ggml-org/llama.cpp:server-cuda` image and rebuilt automatically whenever llama.cpp publishes a new server image. Workers require hosts with CUDA **12.8+** (the template pins allowed CUDA versions).

---

## What this template is optimized for

- **5 × ~256k context** concurrent on a single large-VRAM GPU (implemented as a shared total context split across 5 parallel slots).
- Can be adjusted to **1 × ~1M context** per worker by setting a single parallel slot and an appropriate context size.
- KV cache quantization defaults to **q8_0**. If you need more concurrency / context headroom and can accept some quality loss, switch KV cache to **q4_0**.
- The Hugging Face model repos used for this worker are maintained under **The-Bureau-of-Readiness/** and are intentionally trimmed to include only the files needed for the selected configuration (to avoid large “download-the-entire-repo” cold starts).

This repo also refactors caching behavior to avoid crash-loops:
- If cached-model settings are provided but the cache is missing, the worker **falls back to downloading** instead of exiting.

---

## Quick start

1. Deploy the template.
2. Set **Model** (`LLAMA_ARG_HF_REPO`) to one of the trimmed repos, e.g.
   - `The-Bureau-of-Readiness/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`
   - `The-Bureau-of-Readiness/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`
3. If the repo is vision-capable, set **MMProj file in Repo** (`MMPROJ_HF_FILE`) to the mmproj filename in that same repo, e.g.
   - `mmproj-Qwen3.8-Flash-Next-BF16.gguf`
4. Choose a GPU with enough VRAM for the model + KV cache (long context is KV-cache heavy).
5. Adjust **Context Size**, **Parallel Slots**, **KV cache types**, etc.

---

## Configuration

Most important settings, available in the template UI:

| Setting | Meaning |
|---|---|
| Model (`LLAMA_ARG_HF_REPO`) | Hugging Face GGUF repo, `<owner>/<repo>` (use the trimmed repos under `The-Bureau-of-Readiness/`) |
| Quantization (`LLAMA_HF_QUANT`) | Quant tag (ignored when `LLAMA_ARG_HF_FILE` is set) |
| GGUF File in Repo (`LLAMA_ARG_HF_FILE`) | Exact `.gguf` path inside the repo (use for sharded files like `...-00001-of-00002.gguf` or files in subfolders) |
| MMProj file in Repo (`MMPROJ_HF_FILE`) | **Vision**: mmproj filename/path inside the same repo (resolved from HF cache and set as `LLAMA_ARG_MMPROJ`) |
| HF token (`HF_TOKEN`) | Token for gated/private repos (mapped internally to `HUGGINGFACE_HUB_TOKEN`) |
| HF cache root (`HF_HOME`) | Set to `/runpod-volume/huggingface-cache` when using a mounted volume to persist downloads |
| Context Size (`LLAMA_ARG_CTX_SIZE`) | **Total** context across all parallel slots |
| Parallel Slots (`LLAMA_ARG_N_PARALLEL`) | Number of concurrent requests per worker |
| Max Concurrency (`MAX_CONCURRENCY`) | Max RunPod jobs accepted concurrently per worker (recommended: set equal to `LLAMA_ARG_N_PARALLEL`) |
| GPU Layers (`LLAMA_ARG_N_GPU_LAYERS`) | 999 = all layers on GPU |
| Flash Attention (`LLAMA_ARG_FLASH_ATTN`) | Recommended `on` |
| KV cache type K/V (`LLAMA_ARG_CACHE_TYPE_K` / `LLAMA_ARG_CACHE_TYPE_V`) | q8_0 default; q4_0 uses less VRAM with more quality loss |
| Batch / Ubatch (`LLAMA_ARG_BATCH` / `LLAMA_ARG_UBATCH`) | Prompt-ingestion speed vs memory tradeoff. If you OOM during prefill, lower `UBATCH` first. |
| Extra llama-server args (`LLAMA_SERVER_CMD_ARGS`) | Passed verbatim; never set `--port` |

### Important gotcha: context is shared across slots
`LLAMA_ARG_CTX_SIZE` is shared across `LLAMA_ARG_N_PARALLEL`.

Example:
- ctx=1,310,720 and slots=5
- per-slot ≈ 1,310,720 / 5 = 262,144 tokens (~256k)

---

## Calling the endpoint

### OpenAI-compatible API (recommended)
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1",
    api_key="<YOUR_RUNPOD_API_KEY>",
)
```

### RunPod queue API
```json
{ "input": { "prompt": "Hello, who are you?", "stream": false } }
```

```json
{ "input": { "messages": [{ "role": "user", "content": "Hello!" }], "stream": true } }
```

Or call OpenAI routes explicitly:
```json
{
  "input": {
    "openai_route": "/v1/chat/completions",
    "openai_input": {
      "model": "any",
      "messages": [{ "role": "user", "content": "Hello!" }],
      "stream": true
    }
  }
}
```

---

## Downloads and caching (recommended)

### Default behavior (no caching configured)
If you set only `LLAMA_ARG_HF_REPO` (and optionally `LLAMA_HF_QUANT` / `LLAMA_ARG_HF_FILE`), `llama-server` downloads the model on worker cold start.

> Note: the recommended repos under `The-Bureau-of-Readiness/` are intentionally trimmed so cold starts don’t pull unnecessary extra quants/files.

### Persistent caching on `/runpod-volume` (recommended)
If you attach persistent storage mounted at `/runpod-volume`, set:

- `HF_HOME=/runpod-volume/huggingface-cache`

This makes Hugging Face use:

- `/runpod-volume/huggingface-cache/hub`

so subsequent cold starts reuse the cached snapshots.

### Cached model path resolution (optional)
You can also provide:

- `LLAMA_CACHED_MODEL` = HF repo id
- `LLAMA_CACHED_GGUF_PATH` = GGUF path inside that repo

If set, the worker tries to resolve the GGUF from the HF cache first. If it’s not found yet, the worker falls back to downloading and will use the cache on later starts.

### Sharded models
For sharded GGUF files like `...-00001-of-00002.gguf`, always point `LLAMA_ARG_HF_FILE` / `LLAMA_CACHED_GGUF_PATH` to the **first shard** (`00001-of-00002.gguf`).

### Debugging cache resolution
```bash
python ./find_cached.py <owner>/<repo> <path/inside/repo.gguf>
```

---

## Metrics (optional)

If enabled, llama.cpp can expose Prometheus-format metrics via `--metrics`.

Recommended toggles (if you wired these into `hub.json` and `start.sh`):

- `ENABLE_METRICS=true` (or `1`)
- `METRICS_PORT=8080`

If you also configured the optional Pushgateway pusher:

- `PUSHGATEWAY_URL=http://your-pushgateway:9091`
- `PUSHGATEWAY_JOB=llamacpp-serverless`
- `PUSH_INTERVAL_SECONDS=2`

---

## Docker (local test or use direct in other provider)

### Build
```bash
docker build -t llama-cpp-runpod:test .
```

### Run
```bash
docker run --rm -it --gpus all \
  -e HF_HOME=/tmp/hf-cache \
  -e LLAMA_ARG_HF_REPO=The-Bureau-of-Readiness/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF \
  -e MMPROJ_HF_FILE=mmproj-Qwen3.8-Flash-Next-BF16.gguf \
  -e LLAMA_ARG_CTX_SIZE=262144 \
  -e LLAMA_ARG_N_PARALLEL=1 \
  -e MAX_CONCURRENCY=1 \
  -e LLAMA_ARG_N_GPU_LAYERS=999 \
  -e LLAMA_ARG_FLASH_ATTN=on \
  -e LLAMA_ARG_CACHE_TYPE_K=q8_0 \
  -e LLAMA_ARG_CACHE_TYPE_V=q8_0 \
  -e LLAMA_ARG_BATCH=2048 \
  -e LLAMA_ARG_UBATCH=1024 \
  -e LLAMA_SERVER_CMD_ARGS="-lm mmap --lazy-mode on" \
  llama-cpp-runpod:test
```

---

## License

See the [LICENSE](./LICENSE) file.
