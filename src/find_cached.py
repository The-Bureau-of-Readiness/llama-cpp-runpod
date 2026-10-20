"""
Finds the full LLM GGUF path from the Hugging Face cache.
"""

import os
import sys
import argparse

DEFAULT_CACHE_DIR = "/runpod-volume/huggingface-cache/hub"


def get_cache_dir() -> str:
    # Prefer explicit hub cache path if provided.
    hub_cache = os.getenv("HUGGINGFACE_HUB_CACHE")
    if hub_cache:
        return hub_cache

    # If HF_HOME is set, HF hub cache is typically at $HF_HOME/hub.
    hf_home = os.getenv("HF_HOME")
    if hf_home:
        return os.path.join(hf_home, "hub")

    return DEFAULT_CACHE_DIR


def candidate_model_dirs(cache_dir: str, model_name: str):
    # HF uses models--org--repo
    # We try both the provided casing and a lowercase variant, because users often
    # supply different casing in env vars.
    def to_cache_name(name: str) -> str:
        return name.replace("/", "--")

    cache_name_exact = to_cache_name(model_name)
    cache_name_lower = to_cache_name(model_name).lower()

    # Return unique candidates in order.
    seen = set()
    for cache_name in (cache_name_exact, cache_name_lower):
        if cache_name in seen:
            continue
        seen.add(cache_name)
        yield os.path.join(cache_dir, f"models--{cache_name}", "snapshots")


def find_model_path(model_name: str, gguf_in_repo: str) -> str | None:
    cache_dir = get_cache_dir()

    for snapshots_dir in candidate_model_dirs(cache_dir, model_name):
        if not os.path.exists(snapshots_dir):
            continue

        snapshots = [d for d in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, d))]
        if not snapshots:
            continue

        # Pick most recent-ish deterministically (snapshot dirs are hashes; sorting is stable)
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
