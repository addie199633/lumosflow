import logging
import os
import random
import time

import requests


MIN_DELAY_SECONDS = 2 * 60 * 60
MAX_DELAY_SECONDS = 8 * 60 * 60
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "anthropic/claude-haiku-4-5"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def generate_message(openrouter_api_key: str) -> str:
    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENROUTER_MODEL,
            "max_tokens": 120,
            "temperature": 0.9,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You write short Telegram messages in casual Chinese. "
                        "The tone should feel spontaneous, familiar, warm, and a little cheeky. "
                        "Occasionally tease the reader gently, but never be cruel, insulting, or creepy. "
                        "Do not mention that you are an AI or that this was generated. "
                        "Return only the message text."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "写一条适合随机发给熟人的 Telegram 消息。"
                        "像突然想起来就发一句，别太正式，别超过 60 个中文字符。"
                    ),
                },
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    try:
        message = payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenRouter returned an unexpected response") from exc

    if not message:
        raise RuntimeError("OpenRouter returned an empty message")
    return message


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    if not payload.get("ok"):
        description = payload.get("description", "Unknown Telegram API error")
        raise RuntimeError(description)


def sleep_random_interval() -> None:
    delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
    hours = delay / 60 / 60
    logging.info("Next message in %.2f hours", hours)
    time.sleep(delay)


def main() -> None:
    bot_token = require_env("TELEGRAM_BOT_TOKEN")
    chat_id = require_env("TELEGRAM_CHAT_ID")
    openrouter_api_key = require_env("OPENROUTER_API_KEY")

    logging.info("Lumosflow Telegram sender started")

    while True:
        sleep_random_interval()
        try:
            message = generate_message(openrouter_api_key)
            send_telegram_message(bot_token, chat_id, message)
            logging.info("Sent message: %s", message)
        except Exception:
            logging.exception("Failed to generate or send message")


if __name__ == "__main__":
    main()
