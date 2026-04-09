"""AI Analyzer — DeepSeek V3.2 integration via OpenAI SDK.

Streams analysis from DeepSeek and returns structured JSON output.
"""

import json
import logging

from openai import OpenAI

from config import Config
from ai.prompts import build_streaming_prompt

logger = logging.getLogger("cyberpulse.ai.analyzer")


def _repair_truncated_json(content: str) -> str:
    """Attempt to repair a JSON string that was cut off mid-stream.

    Finds the last complete JSON object in the array and closes all open brackets.
    """
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped.rsplit("```", 1)[0].strip()

    # Find last complete JSON entry (ends before the next incomplete one)
    for delimiter in ["        },\n        {", "    },\n    {", "},\n{"]:
        pos = stripped.rfind(delimiter)
        if pos != -1:
            truncated = stripped[:pos + 1]
            break
    else:
        # Fall back to last closing brace
        last_brace = stripped.rfind("}")
        truncated = stripped[:last_brace + 1] if last_brace != -1 else stripped

    # Count open brackets to know what to close
    stack = []
    in_string = False
    escape_next = False
    for ch in truncated:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()

    if not stack:
        return truncated

    closer = {"[": "]", "{": "}"}
    closing = "".join(closer[s] for s in reversed(stack))
    return truncated + "\n" + closing


def _get_client() -> OpenAI:
    """Create an OpenAI client configured for DeepSeek."""
    if not Config.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is not set in .env")
    return OpenAI(
        api_key=Config.DEEPSEEK_API_KEY,
        base_url=Config.DEEPSEEK_BASE_URL,
    )


def analyze_scan(scan_data: dict) -> dict:
    """Send scan data to DeepSeek and return the parsed JSON analysis.

    Args:
        scan_data: Full scan data dict containing results from all modules.

    Returns:
        Parsed JSON dict with analysis, or error dict on failure.
    """
    client = _get_client()
    messages = build_streaming_prompt(scan_data)

    logger.info("Sending scan data to DeepSeek for analysis (target: %s)", scan_data.get("target"))

    try:
        response = client.chat.completions.create(
            model=Config.DEEPSEEK_MODEL,
            messages=messages,
            temperature=Config.DEEPSEEK_TEMPERATURE,
            max_tokens=Config.DEEPSEEK_MAX_TOKENS,
            response_format={"type": "json_object"},
        )

        choice = response.choices[0]
        content = choice.message.content
        finish_reason = choice.finish_reason

        if finish_reason == "length":
            logger.warning("DeepSeek response truncated (finish_reason=length). Attempting JSON repair.")
            content = _repair_truncated_json(content)

        analysis = json.loads(content)
        logger.info("DeepSeek analysis received successfully (finish_reason=%s)", finish_reason)
        return analysis

    except json.JSONDecodeError as e:
        logger.error("Failed to parse DeepSeek response as JSON: %s", e)
        # Try to extract + repair JSON
        try:
            repaired = _repair_truncated_json(content)
            return json.loads(repaired)
        except Exception:
            return {"error": "JSON parse error", "raw_response": content}

    except Exception as e:
        logger.error("DeepSeek API call failed: %s", e)
        return {"error": str(e)}


def analyze_scan_streaming(scan_data: dict):
    """Stream analysis from DeepSeek, yielding chunks of text.

    Yields:
        str: Chunks of the AI response as they arrive.
    """
    client = _get_client()
    messages = build_streaming_prompt(scan_data)

    logger.info("Starting streaming analysis for target: %s", scan_data.get("target"))

    try:
        stream = client.chat.completions.create(
            model=Config.DEEPSEEK_MODEL,
            messages=messages,
            temperature=Config.DEEPSEEK_TEMPERATURE,
            max_tokens=Config.DEEPSEEK_MAX_TOKENS,
            stream=True,
        )

        full_response = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                full_response += delta.content
                yield delta.content

        # Try to parse the full response as JSON at the end
        logger.info("Streaming analysis complete (%d chars)", len(full_response))

    except Exception as e:
        logger.error("Streaming analysis failed: %s", e)
        yield json.dumps({"error": str(e)})


def parse_streaming_response(full_text: str) -> dict:
    """Parse the full streaming response into a structured dict."""
    try:
        return json.loads(full_text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        try:
            start = full_text.index("{")
            end = full_text.rindex("}") + 1
            return json.loads(full_text[start:end])
        except Exception:
            return {
                "error": "Could not parse AI response",
                "raw_text": full_text[:3000],
            }
