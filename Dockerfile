FROM python:3.12-slim

WORKDIR /app

# install system dependencies
RUN apt-get update && apt-get install -y \
    udev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# install arduino-cli
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
RUN arduino-cli core update-index
RUN arduino-cli core install arduino:avr
RUN arduino-cli core install arduino:renesas_uno
RUN arduino-cli core install esp32:esp32

# install python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "flashbot.py"]