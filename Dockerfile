# Use the official lightweight image with Python 3.13 and pre-installed uv
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Set working directory inside the container
WORKDIR /app

# Copy dependency definition files first (for Docker layer caching)
COPY pyproject.toml uv.lock ./

# Install production dependencies without development packages
RUN uv sync --frozen --no-dev

# Copy the rest of application source code
COPY src ./src

# Add virtualenv created by uv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Define the default execution command
CMD ["python", "-m", "src.main"]