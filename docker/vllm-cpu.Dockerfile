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

ENV VLLM_TARGET_DEVICE=cpu
RUN pip install --no-cache-dir -e . --no-build-isolation

EXPOSE 8000
ENTRYPOINT ["python", "-m", "vllm.entrypoints.openai.api_server"]
