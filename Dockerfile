FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY . .
RUN pip install --no-cache-dir .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# CJK fonts so PDF export (fpdf2) can render Chinese reports inside the container
# (issue #48 — the slim image ships no CJK font, so _find_cjk_font() returns None).
RUN echo 'deb http://mirrors.aliyun.com/debian/ bullseye main contrib non-free' > /etc/apt/sources.list \
    && echo 'deb http://mirrors.aliyun.com/debian/ bullseye-updates main contrib non-free' >> /etc/apt/sources.list \
    && echo 'deb http://mirrors.aliyun.com/debian-security/ bullseye-security main contrib non-free' >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser/app

COPY --from=builder --chown=appuser:appuser /build .

ENTRYPOINT ["tradingagents"]
