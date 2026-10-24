FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASHBOT_HOME=/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends udev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# arduino-cli and the cores FlashBot supports out of the box
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh
RUN arduino-cli config init \
    && arduino-cli config add board_manager.additional_urls \
       https://espressif.github.io/arduino-esp32/package_esp32_index.json \
       https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json \
    && arduino-cli update \
    && arduino-cli core install arduino:avr arduino:renesas_uno esp32:esp32 rp2040:rp2040

# PlatformIO Core; platforms are downloaded on first use and cached in the pio volume
RUN pip install platformio

WORKDIR /app
COPY pyproject.toml poetry.lock README.md ./
COPY src/ ./src/
RUN pip install .

WORKDIR /workspace
CMD ["flashbot", "run", "--auto"]
