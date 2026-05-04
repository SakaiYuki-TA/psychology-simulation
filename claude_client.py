"""Groq API クライアント（ファイル名は既存命名に合わせて維持）"""
import os
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(".env に GROQ_API_KEY が設定されていません")
        _client = Groq(api_key=api_key)
    return _client


def query_agent(
    system_prompt: str,
    user_message: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 250,
    retries: int = 3,
) -> str:
    client = get_client()
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise e
