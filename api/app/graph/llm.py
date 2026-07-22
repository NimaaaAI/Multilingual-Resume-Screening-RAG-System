from openai import OpenAI

from api.app.config import settings

_client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def generate(prompt: str) -> str:
    response = _client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
