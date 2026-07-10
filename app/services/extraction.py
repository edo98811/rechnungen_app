import base64
from typing import Literal

import anthropic
from anthropic.types import ImageBlockParam, MessageParam, TextBlockParam

from app.config import settings
from app.models.receipt import Receipt

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SupportedMediaType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]

EXTRACTION_PROMPT = (
    "Extract all line items, prices, and totals from this German supermarket "
    "receipt. Convert German number format (comma as decimal separator) to "
    "standard decimals. Convert the date to ISO 8601 format (YYYY-MM-DD)."
)


def extract_receipt(image_bytes: bytes, media_type: SupportedMediaType) -> Receipt:
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Create the message blocks for the request to the model
    image_block: ImageBlockParam = {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": image_data},
    }

    text_block: TextBlockParam = {"type": "text", "text": EXTRACTION_PROMPT}
    messages: list[MessageParam] = [{"role": "user", "content": [image_block, text_block]}]

    response = client.messages.parse(
        model="claude-opus-4-8",
        max_tokens=4096,
        messages=messages,
        output_format=Receipt,
    )

    if response.parsed_output is None:
        raise ValueError("Claude did not return a parsed receipt")

    return response.parsed_output
    