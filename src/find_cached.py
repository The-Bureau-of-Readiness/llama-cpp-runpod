"""
Finds the full LLM GGUF path from the Hugging Face cache.
"""

import os
import sys
import argparse


def get_cache_dir() -> str:
    hf_home = os.getenv("HF_HOME", "/runpod-volume/huggingface-cache")
    return os.path.join(hf_home.rstrip("/"), "hub")


def candidate_model_dirs(cache_dir: str, model_name: str):
    def to_cache_name(name: str) -> str:
        return name.replace("/", "--")

    cache_name_exact = to_cache_name(model_name)
    cache_name_lower = to_cache_name(model_name).lower()

    seen = set()
    for cache_name in (cache_name_exact, cache_name_lower):
        if cache_name in seen:
            continue
        seen.add(cache_name)
        yield os.path.join(cache_dir, f"models--{cache_name}", "snapshots")


def find_model_path(model_name: str, gguf_in_repo: str) -> str | None:
    model_name = model_name.split(":", 1)[0]  # strip :quant if present
    cache_dir = get_cache_dir()

    for snapshots_dir in candidate_model_dirs(cache_dir, model_name):
        if not os.path.exists(snapshots_dir):
            continue

        snapshots = [
            d for d in os.listdir(snapshots_dir)
            if os.path.isdir(os.path.join(snapshots_dir, d))
        ]
        if not snapshots:
            continue

        snapshots.sort(reverse=True)
        for snap in snapshots:
            candidate = os.path.join(snapshots_dir, snap, gguf_in_repo)
            if os.path.exists(candidate):
                return candidate

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Find the full GGUF path from the Hugging Face cache."
    )
    parser.add_argument("model", type=str, help="The model name from Hugging Face (org/repo)")
    parser.add_argument("path", type=str, help="Path to GGUF file within the repo, e.g. IQ3_S/model-00001-of-00002.gguf")
    args = parser.parse_args()

    cache_dir = get_cache_dir()
    model_path = find_model_path(args.model, args.path)

    if model_path is None:
        print(
            f"Error: Cached model not found. Model='{args.model}', GGUF='{args.path}', Cache dir='{cache_dir}'",
            file=sys.stderr,
        )
        sys.exit(1)

    print(model_path, end="")


if __name__ == "__main__":
    main()
