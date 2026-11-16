# Hugging Face Space (Docker SDK): the web page + the API on port 7860. See DEPLOY.md.
#
# Needs in the build context (the Space repository): chunks.json and embeddings.npy. They are NOT in the
# public GitHub repository; deploy/prepare_space.py copies them into the Space folder. The school documents
# (documents/) are never copied (.dockerignore).

# ---------------------------------------------------------------- 1. web page (React, Vite)
FROM node:22-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# vite.config.js reads the logo from ../public
COPY public/ /build/public/
RUN npm run build


# ---------------------------------------------------------------- 2. API (Python)
FROM python:3.10-slim AS app

# Spaces run the container as user 1000; the model cache must be writable by it.
RUN useradd --create-home --uid 1000 user
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    PATH=/home/user/.local/bin:$PATH
# WORKDIR alone would create the folder as root: the API could not write feedback.jsonl (PermissionError)
RUN install -d -o user -g user /home/user/app
WORKDIR /home/user/app

# torch CPU-only first (a few hundred MB instead of several GB with CUDA); sentence-transformers then finds it
# installed. "+cpu" only exists on the PyTorch index, so the CUDA build from PyPI can't be picked; PyPI stays
# reachable for torch's own dependencies.
RUN pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
        "torch==2.14.1+cpu"
COPY requirements-deploy.txt .
RUN pip install -r requirements-deploy.txt

USER user

# The embedding model is downloaded now, during the build, not at every start.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"
# ...and never again at run time
ENV HF_HUB_OFFLINE=1

COPY --chown=user *.py documents_status.json french_words.txt ./
COPY --chown=user chunks.json embeddings.npy ./
COPY --chown=user --from=frontend /build/frontend/dist ./frontend/dist

EXPOSE 7860
# --proxy-headers: behind the Space's proxy, the client IP comes from X-Forwarded-For. Without it every student
# would have the proxy's IP and share the same 20 requests/minute limit. Trusting any forwarder is fine here
# because only the Space's proxy can reach the container.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
