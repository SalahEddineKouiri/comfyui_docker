# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim

ARG PYTORCH_INSTALL_ARGS=""
ARG EXTRA_ARGS=""

# Fail fast on errors or unset variables
SHELL ["/bin/bash", "-eux", "-o", "pipefail", "-c"]

RUN <<EOF
	apt-get update
	apt-get install -y --no-install-recommends \
		git \
		git-lfs \
		rsync \
		fonts-recommended
EOF

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 gcc build-essential -y

WORKDIR /app

ENV XDG_CACHE_HOME=/cache
ENV PIP_CACHE_DIR=/cache/pip
ENV VIRTUAL_ENV=/app/venv
ENV VIRTUAL_ENV_CUSTOM=/app/custom_venv

# create cache directory
RUN --mount=type=cache,target=/cache/ \
	mkdir -p ${PIP_CACHE_DIR}

# create virtual environment
RUN python -m venv ${VIRTUAL_ENV}

# run python from venv (prefer custom_venv over baked-in one)
ENV PATH="${VIRTUAL_ENV_CUSTOM}/bin:${VIRTUAL_ENV}/bin:${PATH}"

RUN --mount=type=cache,target=/cache/ \
	pip install torch torchvision torchaudio ${PYTORCH_INSTALL_ARGS}

# copy requirements files first so packages can be cached separately
COPY requirements.txt .
RUN --mount=type=cache,target=/cache/ \
	pip install -r requirements.txt

COPY . .

RUN python setup_custom_nodes.py

COPY .git .git

# default environment variables
ENV COMFYUI_ADDRESS=0.0.0.0
ENV COMFYUI_PORT=8188
ENV COMFYUI_EXTRA_BUILD_ARGS="${EXTRA_ARGS}"
ENV COMFYUI_EXTRA_ARGS=""

# default start command
CMD \
	if [ -d "${VIRTUAL_ENV_CUSTOM}" ]; then \
		rsync -aP "${VIRTUAL_ENV}/" "${VIRTUAL_ENV_CUSTOM}/" ;\
		sed -i "s!${VIRTUAL_ENV}!${VIRTUAL_ENV_CUSTOM}!g" "${VIRTUAL_ENV_CUSTOM}/pyvenv.cfg" ;\
	fi ;\
	python -u main.py --listen ${COMFYUI_ADDRESS} --port ${COMFYUI_PORT} ${COMFYUI_EXTRA_BUILD_ARGS} ${COMFYUI_EXTRA_ARGS}
