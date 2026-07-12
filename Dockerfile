FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    udev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install arduino-cli
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
RUN arduino-cli core update-index \
    --additional-urls https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json
RUN arduino-cli core install arduino:avr
RUN arduino-cli core install arduino:renesas_uno
RUN arduino-cli core install esp32:esp32 \
    --additional-urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
RUN arduino-cli core install rp2040:rp2040 \
    --additional-urls https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json

# Install Poetry
RUN pip install poetry

# Copy dependency files first (better layer caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies without creating a venv (we're already in a container)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy source
COPY src/ ./src/
COPY sketches/ ./sketches/

# Entry point via installed CLI command
CMD ["flashbot"]