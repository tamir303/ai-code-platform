# CPU-only vLLM OpenAI-compatible server, built from vLLM's own CPU target.
# NOTE: vLLM's CPU build path evolves between releases — if this build fails,
# check https://github.com/vllm-project/vllm/blob/main/docker/Dockerfile.cpu
# for the current recommended steps and adjust the version tag below.
FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake libnuma-dev \
    && rm -rf /var/lib/apt/lists/*

ARG VLLM_VERSION=v0.6.6
RUN git clone --depth 1 --branch ${VLLM_VERSION} https://github.com/vllm-project/vllm.git .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -v -r requirements-cpu.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Build-system dependencies for vLLM's setup.py. Required because
# --no-build-isolation makes pip skip [build-system].requires entirely, so
# setup.py fails with ModuleNotFoundError: No module named 'setuptools_scm'.
# This mirrors requirements-build.txt from vLLM's own Dockerfile.cpu, minus
# torch — already installed as the +cpu build above, and re-resolving it here
# risks pulling the ~900MB CUDA wheel from the default index.
RUN pip install --no-cache-dir \
    "cmake>=3.26" ninja packaging "setuptools>=61" "setuptools-scm>=8" wheel jinja2

ENV VLLM_TARGET_DEVICE=cpu
RUN pip install --no-cache-dir -e . --no-build-isolation

# Pin drifted transitive deps back to versions contemporary with this vLLM tag.
# requirements-cpu.txt leaves these unbounded, so a fresh resolve picks releases
# far newer than v0.6.6 supports and the engine dies during CPU executor import:
#   triton > 3.1      -> ImportError: cannot import name 'default_cache_dir'
#                        from 'triton.runtime.cache' (vllm/triton_utils)
#   transformers >= 5 -> AttributeError: Qwen2Tokenizer has no attribute
#                        'all_special_tokens_extended'
# triton 3.1.0 is the version matching torch 2.5.1.
RUN pip install --no-cache-dir "transformers>=4.45.2,<5" "triton==3.1.0"

EXPOSE 8000
ENTRYPOINT ["python", "-m", "vllm.entrypoints.openai.api_server"]
