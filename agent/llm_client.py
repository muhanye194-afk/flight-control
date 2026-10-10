import os
from typing import Dict, List, Type, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from agent.schemas import InvestigationReport

load_dotenv()

MODEL_NAME = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-sol"
)
REQUEST_TIMEOUT_SECONDS = float(
    os.getenv("OPENAI_TIMEOUT_SECONDS", "90")
)
MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))

T = TypeVar("T", bound=BaseModel)


def get_openai_client() -> OpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "未找到 OPENAI_API_KEY。请在 .env 中配置真实 Key。"
        )

    return OpenAI(
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=MAX_RETRIES,
    )


def parse_structured_response(
    messages: List[Dict[str, str]],
    response_model: Type[T]
) -> T:
    client = get_openai_client()

    response = client.responses.parse(
        model=MODEL_NAME,
        input=messages,
        text_format=response_model
    )

    if response.output_parsed is None:
        raise RuntimeError(
            "LLM 没有返回可解析的结构化结果。"
        )

    return response.output_parsed


def investigate_with_llm(
    messages: List[Dict[str, str]]
) -> InvestigationReport:
    return parse_structured_response(
        messages,
        InvestigationReport
    )
