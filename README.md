[![Runpod](https://api.runpod.io/badge/The-Bureau-of-Readiness/llama-cpp-runpod)](https://console.runpod.io/hub/listing/The-Bureau-of-Readiness/llama-cpp-runpod)

<p align="center">
    <img src="https://raw.githubusercontent.com/ggml-org/llama.cpp/master/media/llama1-icon-transparent.png" alt="llama.cpp logo" width="128">
</p>

# llama.cpp on RunPod Serverless

Serve any GGUF model from Hugging Face as a RunPod **serverless** endpoint, powered by [llama.cpp](https://github.com/ggml-org/llama.cpp)’s `llama-server`.

This worker exposes an OpenAI-compatible API:

- `/v1/models`
- `/v1/chat/completions`
- `/v1/completions`

Streaming is supported.

The Docker image is built on the official `ghcr.io/ggml-org/llama.cpp:server-cuda` image and is rebuilt automatically when llama.cpp publishes a new server image. Each release of this template is named after the llama.cpp build it ships (e.g. `b10666`). Because the base image tracks a recent CUDA toolkit, workers require hosts with CUDA **12.8+** (the template pins allowed CUDA versions automatically).

---

## Quick start

1. Deploy the template.
2. Pick a **Model** (`LLAMA_ARG_HF_REPO`): a Hugging Face GGUF repo, e.g. `unsloth/Qwen3.8-27B-GGUF`.
3. Pick a **Quantization** (`LLAMA_HF_QUANT`): e.g. `Q4_K_M` or `UD-Q4_K_XL` (must match a GGUF file/tag in the repo).  
   - If the model is sharded or has unusual filenames, set **GGUF File in Repo** (`LLAMA_ARG_HF_FILE`) instead.
4. Choose a GPU with enough VRAM for:
   - the GGUF weights, plus
   - the KV cache (context size dependent).
5. Adjust **Context Size**, **Parallel Slots**, and advanced options as needed.

By default, the model is downloaded from Hugging Face on worker cold start. For faster cold starts after the first run, enable caching (see below).

---

## Configuration

The most important settings, all available in the template UI:

| Setting | Meaning |
|---|---|
| Model (`LLAMA_ARG_HF_REPO`) | Hugging Face GGUF repo, `<owner>/<repo>` |
| Quantization (`LLAMA_HF_QUANT`) | Which quantization/tag to use (ignored when `LLAMA_ARG_HF_FILE` is set) |
| GGUF File in Repo (`LLAMA_ARG_HF_FILE`) | Exact `.gguf` path inside the repo (use for sharded files like `...-00001-of-00002.gguf` or files in subfolders) |
| Context Size (`LLAMA_ARG_CTX_SIZE`) | Total context window in tokens, shared across parallel slots |
| Parallel Slots (`LLAMA_ARG_N_PARALLEL`) | Requests served simultaneously per worker |
| GPU Layers (`LLAMA_ARG_N_GPU_LAYERS`) | Layers offloaded to the GPU (999 = all) |
| CPU MoE Layers (`LLAMA_ARG_N_CPU_MOE`) | MoE only: keep expert weights of first N layers on CPU |
| Flash Attention / KV Cache Types | Speed and VRAM trade-offs for the KV cache |
| Extra llama-server Arguments (`LLAMA_SERVER_CMD_ARGS`) | Any other `llama-server` flags passed verbatim (**never set `--port`**) |
| Max Concurrency per Worker (`MAX_CONCURRENCY`) | Max RunPod jobs accepted concurrently by one worker. Recommended: set equal to `LLAMA_ARG_N_PARALLEL` (or slightly above). |

Most settings map directly to `llama-server` options via its `LLAMA_ARG_*` environment variables.

If your model repo is gated/private, set **Hugging Face Token** (`HF_TOKEN`).

---

## Calling the endpoint

### OpenAI-compatible API (recommended)
Point any OpenAI SDK at your endpoint URL, using your RunPod API key:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.runpod.ai/v2/<ENDPOINT_ID>/openai/v1",
    api_key="<YOUR_RUNPOD_API_KEY>",
)
```

### RunPod queue API
You can also use the RunPod queue API (`POST /v2/<ENDPOINT_ID>/run`):

```json
{ "input": { "prompt": "Hello, who are you?", "stream": false } }
```

```json
{ "input": { "messages": [{ "role": "user", "content": "Hello!" }], "stream": true } }
```

Or call OpenAI routes explicitly via the queue input:

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

## Downloads and caching (read this if your model is large)

This worker supports **two** ways to avoid repeatedly downloading large GGUFs.

### 1) Default behavior: download from Hugging Face on cold start
If you only set `LLAMA_ARG_HF_REPO` (and optionally `LLAMA_HF_QUANT` / `LLAMA_ARG_HF_FILE`), `llama-server` downloads the model when a worker starts.

This is simplest, but slow for large models.

### 2) Persistent cache on `/runpod-volume` (recommended for large models)
If you attach a persistent volume (“global store”) mounted at `/runpod-volume`, you can make Hugging Face store its cache there. The first cold start downloads once; subsequent cold starts re-use the cache.

Set:

- `HF_HOME=/runpod-volume/huggingface-cache`

That makes the Hugging Face hub cache live at:

- `/runpod-volume/huggingface-cache/hub`

### 3) Cached model path resolution (optional; speeds up and avoids re-downloading)
This worker can resolve a GGUF path directly from the Hugging Face cache (instead of downloading) using:

- `LLAMA_CACHED_MODEL` (HF repo id, e.g. `unsloth/Qwen3.8-27B-GGUF`)
- `LLAMA_CACHED_GGUF_PATH` (path to GGUF inside the repo, e.g. `Qwen3.8-27B-Q4_K_M.gguf` or `IQ3_S/...-00001-of-00002.gguf`)

**Behavior:**
- If the GGUF is already present in the cache, the worker starts `llama-server` with `-m <resolved path>` (fast).
- If it is not present yet, the worker falls back to downloading from Hugging Face (warming the cache for future starts).

### Sharded models (`...-00001-of-00002.gguf`)
If your repo contains shards like `...-00001-of-00002.gguf` and `...-00002-of-00002.gguf`, point `LLAMA_ARG_HF_FILE` and/or `LLAMA_CACHED_GGUF_PATH` at the **first shard** (`00001-of-00002.gguf`). Ensure all shards exist in the repo; they must be downloaded into the same snapshot directory.

### Debugging cache resolution
To see whether the cache contains your model:

```bash
python ./find_cached.py <owner>/<repo> <path/inside/repo.gguf>
```

It prints the resolved absolute path, or exits with an error if the model is not cached (or if the repo/path doesn’t match).

---

## Docker Run

```bash
docker run --rm -it --gpus all \
  -e HF_HOME=/tmp/hf-cache \
  -e LLAMA_ARG_HF_REPO=ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF \
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

## License

See the [LICENSE](./LICENSE) file.
