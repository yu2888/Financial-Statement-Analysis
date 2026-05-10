"""Shared LLM utilities: PDF rendering, image encoding, JSON parsing, streaming."""

import base64
import json
import re
from io import BytesIO

import fitz  # PyMuPDF
from openai import OpenAI
from PIL import Image

MAX_RETRIES = 3


def pdf_page_to_image(pdf_path: str, page_num: int, dpi: int = 200) -> Image.Image:
    """Convert a single page of a PDF to a PIL Image using PyMuPDF."""
    with fitz.open(pdf_path) as doc:
        if page_num >= len(doc):
            raise IndexError(f"Page {page_num + 1} out of range ({len(doc)} pages)")
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        pix = doc[page_num].get_pixmap(matrix=matrix)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def image_to_base64(img: Image.Image) -> str:
    """Encode a PIL Image as a base64 data string."""
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def parse_json_response(raw: str) -> dict:
    """Extract and parse JSON from an LLM response, handling markdown fences and noise."""
    raw = raw.strip()

    # Strip markdown fences (```json ... ``` or ``` ... ```)
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
    raw = re.sub(r"\n?```\s*$", "", raw)
    raw = raw.strip()

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first { ... } block via greedy regex
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise ValueError(f"No valid JSON found in response: {raw[:200]}")


def stream_response(client: OpenAI, model: str, messages: list[dict], verbose: bool = False) -> tuple[str, str, dict | None]:
    """Stream a chat completion, optionally printing thinking + content tokens live.

    Args:
        verbose: If True, print streaming tokens to stdout. Default False.

    Returns:
        (thinking_text, content_text, usage_dict or None)
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
        max_tokens=16000,
        temperature=1.0,
        top_p=0.95,
        presence_penalty=1.5,
        extra_body={
            "top_k": 20,
        },
    )

    thinking = False
    thinking_text = ""
    content_text = ""
    usage = None

    for chunk in response:
        if hasattr(chunk, "usage") and chunk.usage:
            usage = chunk.usage.model_dump()
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        reasoning = getattr(delta, "reasoning", None)
        if reasoning:
            if not thinking:
                if verbose:
                    print("  💭 ", end="", flush=True)
                thinking = True
            thinking_text += reasoning
            if verbose:
                print(reasoning, end="", flush=True)
            continue

        if delta.content:
            if thinking:
                if verbose:
                    print("\n  📝 ", end="", flush=True)
                thinking = False
            content_text += delta.content
            if verbose:
                print(delta.content, end="", flush=True)

    if verbose:
        print()
    return thinking_text, content_text, usage
