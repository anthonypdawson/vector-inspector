###############################################
# Stage 1 — Builder (PDM + dependencies)
###############################################
FROM python:3.12 AS builder

ENV PDM_USE_VENV=true
ENV PDM_IGNORE_SAVED_PYTHON=true

# Qt + build deps
RUN apt-get update && apt-get install -y \
build-essential \
libgl1 \
libxkbcommon-x11-0 \
libxcb1 \
libx11-xcb1 \
libxcb-render0 \
libxcb-shape0 \
libxcb-xfixes0 \
&& rm -rf /var/lib/apt/lists/*

# Install PDM
RUN pip install --upgrade pip && pip install pdm

WORKDIR /app

# Copy metadata first for caching
COPY pyproject.toml pdm.lock ./

# Install production dependencies
RUN pdm install --prod --no-editable

# Copy full project
COPY . .

###############################################
# Stage 2 — Runtime (GUI + VNC + noVNC)
###############################################
FROM python:3.12-slim AS runtime

# Install Qt runtime + VNC + noVNC + window manager
RUN apt-get update && apt-get install -y \
libgl1 \
libxkbcommon-x11-0 \
libxcb1 \
libx11-xcb1 \
libxcb-render0 \
libxcb-shape0 \
libxcb-xfixes0 \
fluxbox \
tigervnc-standalone-server \
websockify \
novnc \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /app

# Expose noVNC port
EXPOSE 8080

# Startup script for VNC + noVNC + VI
RUN printf '#!/bin/bash\n\
mkdir -p /root/.vnc\n\
echo "password" | vncpasswd -f > /root/.vnc/passwd\n\
chmod 600 /root/.vnc/passwd\n\
fluxbox &\n\
tigervncserver :1 -geometry 1280x800 -localhost no\n\
websockify --web=/usr/share/novnc/ 8080 localhost:5901 &\n\
python -m vector_inspector\n' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]