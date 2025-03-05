# Glider 

## Requirements
- Python 3.8+
- [A Discord bot token](https://www.writebots.com/discord-bot-token/)
- [A valid Space API endpoint](https://spaceapi.io/)
- [Channel ID Number](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID#h_01HRSTXPS5FMK2A5SMVSX4JW4E)
- Required Python dependencies (see `pyproject.toml`)
- Poetry

## Installation

### 1. Clone the Repository
```sh
git clone https://github.com/hs3city/glider
cd glider
```

### 2. Create a Virtual Environment
```sh
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
#### Using `poetry`
```sh
poetry install
```

### 4. Set Up Environment Variables
Create a `.env` file or export these variables:
```sh
export DISCORD_TOKEN='your-discord-bot-token'
export SPACE_ENDPOINT='https://your-space-api-endpoint.com/'
export DISCORD_CHANNEL_ID='your-discord-channel-id'
```

### 5. Run the Bot
```sh
python bot.py
```
Or with `poetry`:
```sh
poetry run python bot.py
```

## Docker Deployment
A `Dockerfile` is included for containerized deployment.

### Build the Docker Image
```sh
docker build -t glider .
```

### Run the Container
```sh
docker run -e DISCORD_TOKEN='discord-bot-token' \
           -e SPACE_ENDPOINT='https://your-space-api-endpoint.com/' \
           -e DISCORD_CHANNEL_ID='your-discord-channel-id' \
           glider
```

## Configuration
- **`res/glider_closed.png` & `res/glider_open.png`**: Bot avatars for different statuses.
- **`poetry.lock`**: Python dependencies.
- **`ruff.toml`**: Linter configuration.

## Contributing
1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Submit a pull request.

## License
This project is licensed under the terms of the [MIT](LICENSE) file.
