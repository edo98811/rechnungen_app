from datetime import date
from typing import Literal

from google import genai
from google.genai import types

from app.config import settings
from app.models.receipt import Receipt

client = genai.Client(api_key=settings.gemini_api_key or "unset")

SupportedMediaType = Literal["image/jpeg", "image/png", "image/gif", "image/webp"]

EXTRACTION_PROMPT = (
    "Extract all line items, prices, and totals from this German supermarket "
    "receipt. Convert German number format (comma as decimal separator) to "
    "standard decimals. Convert the date to ISO 8601 format (YYYY-MM-DD)."
)


def extract_receipt(image_bytes: bytes, media_type: SupportedMediaType) -> Receipt:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured (see .env.example)")

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=media_type),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Receipt,
        ),
    )

    if response.text is None:
        raise ValueError("Gemini did not return a parsed receipt")

    receipt = Receipt.model_validate_json(response.text)

    try:
        date.fromisoformat(receipt.date)
    except ValueError:
        receipt.date = date.today().isoformat()

    return receipt
