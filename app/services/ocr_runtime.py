import base64
from difflib import SequenceMatcher
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import UploadFile

from app.core.config import Settings
from app.services.demo_data import demo_profile


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

FIELD_LABELS = {
    "age": "나이",
    "sex": "성별",
    "height_cm": "신장",
    "weight_kg": "체중",
    "waist_cm": "허리둘레",
    "systolic_bp": "수축기혈압",
    "diastolic_bp": "이완기혈압",
    "fasting_glucose": "공복혈당",
    "total_cholesterol": "총콜레스테롤",
    "hdl": "HDL",
    "ldl": "LDL",
    "triglyceride": "중성지방",
}

NUMERIC_RANGES = {
    "age": (19, 100, int),
    "height_cm": (120, 230, float),
    "weight_kg": (30, 200, float),
    "waist_cm": (40, 160, float),
    "systolic_bp": (70, 240, int),
    "diastolic_bp": (40, 160, int),
    "fasting_glucose": (50, 400, int),
    "total_cholesterol": (80, 400, int),
    "hdl": (10, 150, int),
    "ldl": (30, 300, int),
    "triglyceride": (30, 800, int),
}

FIELD_ALIASES = {
    "age": ["age", "나이", "연령", "연령대", "만나이"],
    "sex": ["sex", "성별", "gender"],
    "height_cm": ["height_cm", "height", "신장", "키", "신장cm"],
    "weight_kg": ["weight_kg", "weight", "체중", "몸무게", "체중kg"],
    "waist_cm": ["waist_cm", "waist", "허리둘레", "복부둘레", "waistcircumference"],
    "systolic_bp": ["systolic_bp", "systolic", "수축기혈압", "최고혈압", "혈압최고", "혈압", "bp", "sbp"],
    "diastolic_bp": ["diastolic_bp", "diastolic", "이완기혈압", "최저혈압", "혈압최저", "혈압", "bp", "dbp"],
    "fasting_glucose": ["fasting_glucose", "glucose", "공복혈당", "식전혈당", "혈당", "fbs"],
    "total_cholesterol": ["total_cholesterol", "total_chol", "총콜레스테롤", "총콜레스테롤검사", "콜레스테롤", "tchol", "tc"],
    "hdl": ["hdl", "HDL", "HDL콜레스테롤", "고밀도콜레스테롤", "고밀도지단백"],
    "ldl": ["ldl", "LDL", "LDL콜레스테롤", "저밀도콜레스테롤", "저밀도지단백"],
    "triglyceride": ["triglyceride", "triglycerides", "tg", "중성지방", "트리글리세라이드", "trig"],
}

STRUCTURED_LABEL_KEYS = {
    "label",
    "name",
    "item",
    "field",
    "test",
    "test_name",
    "검사항목",
    "항목",
    "항목명",
    "검사명",
}
STRUCTURED_VALUE_KEYS = {"value", "result", "measurement", "수치", "결과", "검사결과", "측정값"}


class OcrRuntimeError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class UploadedDocument:
    filename: str
    content_type: str
    content: bytes


def ocr_status(settings: Settings) -> dict:
    provider = settings.ocr_provider.lower()
    return {
        "provider": provider,
        "enabled": provider != "demo" and settings.has_openai_key,
        "fallback_to_demo": settings.ocr_fallback_to_demo,
        "max_upload_mb": round(settings.ocr_max_upload_bytes / 1_000_000, 1),
        "model": settings.openai_ocr_model if provider == "openai" else None,
    }


def demo_ocr_result(
    filename: str | None = None,
    content_type: str | None = None,
    *,
    status: str = "demo_extracted",
    message: str | None = None,
    provider: str = "demo",
    warnings: list[str] | None = None,
) -> dict:
    return {
        "filename": filename,
        "content_type": content_type,
        "status": status,
        "provider": provider,
        "message": message
        or "OCR 데모: 검진 결과지에서 주요 수치를 추출한 것처럼 입력폼을 채웠습니다.",
        "prefill": demo_profile(),
        "extracted_fields": [
            "수축기혈압",
            "이완기혈압",
            "공복혈당",
            "총콜레스테롤",
            "HDL",
            "LDL",
            "중성지방",
        ],
        "warnings": warnings or [],
    }


async def extract_checkup_values_from_upload(file: UploadFile, settings: Settings) -> dict:
    document = await _read_upload(file, settings)
    provider = settings.ocr_provider.lower()

    if provider in {"demo", "off", "disabled"}:
        return demo_ocr_result(
            document.filename,
            document.content_type,
            message=(
                "OCR 데모 모드입니다. OPENAI_API_KEY와 OCR_PROVIDER=openai를 설정하면 "
                "업로드 이미지/PDF에서 수치를 실제 추출합니다."
            ),
        )

    if provider != "openai":
        return _fallback_or_error(
            settings,
            document,
            f"지원하지 않는 OCR_PROVIDER={settings.ocr_provider} 값입니다.",
        )

    if not settings.has_openai_key:
        return _fallback_or_error(
            settings,
            document,
            "OPENAI_API_KEY가 없어 OCR 데모 값으로 대체했습니다.",
            status="ocr_fallback_demo",
        )

    try:
        raw_fields = await _extract_with_openai(document, settings)
        return _build_prefill_from_fields(document, raw_fields, settings)
    except Exception as exc:
        if settings.ocr_fallback_to_demo:
            return demo_ocr_result(
                document.filename,
                document.content_type,
                status="ocr_fallback_demo",
                provider="openai",
                message=f"OCR 처리 중 오류가 발생해 데모 값으로 대체했습니다. 원인: {exc}",
                warnings=["실제 제출 전 OCR 키와 샘플 검진표로 재검증이 필요합니다."],
            )
        if isinstance(exc, OcrRuntimeError):
            raise
        raise OcrRuntimeError(f"OCR 처리 중 오류가 발생했습니다: {exc}") from exc


async def _read_upload(file: UploadFile, settings: Settings) -> UploadedDocument:
    content = await file.read(settings.ocr_max_upload_bytes + 1)
    if len(content) > settings.ocr_max_upload_bytes:
        raise OcrRuntimeError(
            f"OCR 업로드 파일은 {round(settings.ocr_max_upload_bytes / 1_000_000, 1)}MB 이하만 지원합니다.",
            status_code=413,
        )
    if not content:
        raise OcrRuntimeError("업로드 파일이 비어 있습니다.", status_code=400)

    return UploadedDocument(
        filename=file.filename or "checkup-document",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )


async def _extract_with_openai(document: UploadedDocument, settings: Settings) -> dict[str, Any]:
    content_items: list[dict[str, Any]] = [{"type": "input_text", "text": _ocr_prompt()}]
    encoded = base64.b64encode(document.content).decode("ascii")

    if document.content_type == "application/pdf" or document.filename.lower().endswith(".pdf"):
        content_items.append(
            {
                "type": "input_file",
                "filename": document.filename,
                "file_data": encoded,
            }
        )
    elif document.content_type.startswith("image/"):
        content_items.append(
            {
                "type": "input_image",
                "image_url": f"data:{document.content_type};base64,{encoded}",
                "detail": "high",
            }
        )
    else:
        raise OcrRuntimeError(
            "OCR은 이미지 파일 또는 PDF만 지원합니다.",
            status_code=415,
        )

    request_body = {
        "model": settings.openai_ocr_model,
        "input": [{"role": "user", "content": content_items}],
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.ocr_request_timeout_seconds) as client:
        response = await client.post(OPENAI_RESPONSES_URL, headers=headers, json=request_body)

    if response.status_code >= 400:
        raise OcrRuntimeError(
            f"OpenAI OCR API 오류 {response.status_code}: {_short_error(response.text)}",
            status_code=502,
        )

    text = _extract_response_text(response.json())
    if not text:
        raise OcrRuntimeError("OpenAI OCR 응답에서 텍스트 결과를 찾지 못했습니다.")

    try:
        return _parse_json_object(text)
    except OcrRuntimeError:
        return {
            "raw_text": text,
            "warnings": ["OpenAI 응답이 JSON 형식이 아니어서 텍스트 기반 AI 매칭 파서를 적용했습니다."],
        }


def _ocr_prompt() -> str:
    return """
You are extracting numeric health checkup values from a Korean health examination result.
Return only one JSON object. Do not include markdown.

JSON schema:
{
  "health": {
    "age": number|null,
    "sex": "male"|"female"|null,
    "height_cm": number|null,
    "weight_kg": number|null,
    "waist_cm": number|null,
    "systolic_bp": number|null,
    "diastolic_bp": number|null,
    "fasting_glucose": number|null,
    "total_cholesterol": number|null,
    "hdl": number|null,
    "ldl": number|null,
    "triglyceride": number|null
  },
  "extracted_fields": string[],
  "warnings": string[]
}

Rules:
- Extract only values visible in the document.
- Use null when a value is missing or uncertain.
- Convert Korean labels such as 수축기혈압, 이완기혈압, 식전혈당(공복혈당), HDL콜레스테롤, LDL콜레스테롤, 트리글리세라이드.
- If the table is hard to structure, include the visible OCR text in "raw_text".
- Do not diagnose disease and do not recommend medication.
""".strip()


def _build_prefill_from_fields(
    document: UploadedDocument,
    raw_fields: dict[str, Any],
    settings: Settings,
) -> dict:
    profile = demo_profile()
    health_fields = raw_fields.get("health") if isinstance(raw_fields.get("health"), dict) else raw_fields
    extracted: list[str] = []
    warnings = list(raw_fields.get("warnings") or []) if isinstance(raw_fields.get("warnings"), list) else []
    match_details: dict[str, dict[str, Any]] = {}

    for field in FIELD_LABELS:
        value, match = _find_field_value(health_fields, field, raw_fields)
        if value is None:
            continue

        if field == "sex":
            sex = _normalize_sex(value)
            if sex:
                profile["health"]["sex"] = sex
                extracted.append(FIELD_LABELS[field])
                match_details[field] = match
            else:
                warnings.append(f"{FIELD_LABELS[field]} 값이 남성/여성으로 해석되지 않아 반영하지 않았습니다.")
            continue

        converted = _coerce_numeric(field, value)
        if converted is None:
            warnings.append(f"{FIELD_LABELS[field]} 값이 허용 범위를 벗어나 반영하지 않았습니다.")
            continue

        profile["health"][field] = converted
        extracted.append(FIELD_LABELS[field])
        match_details[field] = match

    extracted_from_model = raw_fields.get("extracted_fields")
    if isinstance(extracted_from_model, list):
        for item in extracted_from_model:
            if isinstance(item, str) and item not in extracted:
                extracted.append(item)

    if not extracted:
        return _fallback_or_error(
            settings,
            document,
            "OCR 결과에서 반영 가능한 검진 수치를 찾지 못해 데모 값으로 대체했습니다.",
            status="ocr_fallback_demo",
        )

    unknown_checkup_fields = [
        field
        for field in ("systolic_bp", "diastolic_bp", "fasting_glucose", "total_cholesterol", "hdl", "ldl", "triglyceride")
        if field not in match_details
    ]
    for field in unknown_checkup_fields:
        profile["health"][field] = None
    profile["health"]["unknown_fields"] = unknown_checkup_fields
    profile["health"]["bp_unknown"] = {"systolic_bp", "diastolic_bp"}.issubset(unknown_checkup_fields)
    profile["health"]["glucose_unknown"] = "fasting_glucose" in unknown_checkup_fields
    profile["health"]["lipid_unknown"] = {"total_cholesterol", "hdl", "ldl", "triglyceride"}.issubset(unknown_checkup_fields)

    return {
        "filename": document.filename,
        "content_type": document.content_type,
        "status": "ocr_extracted",
        "provider": "openai",
        "message": "OCR 결과를 입력폼에 반영했습니다. 분석 전 수치가 맞는지 사용자가 반드시 확인해야 합니다.",
        "prefill": profile,
        "extracted_fields": extracted,
        "raw_fields": raw_fields,
        "match_details": match_details,
        "warnings": warnings,
        "model": settings.openai_ocr_model,
    }


def _fallback_or_error(
    settings: Settings,
    document: UploadedDocument,
    message: str,
    *,
    status: str = "ocr_fallback_demo",
) -> dict:
    if settings.ocr_fallback_to_demo:
        return demo_ocr_result(
            document.filename,
            document.content_type,
            status=status,
            provider=settings.ocr_provider.lower(),
            message=message,
            warnings=["데모 fallback으로 입력폼을 채웠습니다."],
        )
    raise OcrRuntimeError(message, status_code=503)


def _extract_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text

    texts: list[str] = []
    for item in payload.get("output", []):
        if isinstance(item, dict) and isinstance(item.get("content"), list):
            for content in item["content"]:
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str) and content.get("type") in {"output_text", "text"}:
                    texts.append(text)
        elif isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str):
                texts.append(text)
    return "\n".join(texts).strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    elif not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise OcrRuntimeError("OCR 응답이 JSON 형식이 아닙니다.")
        stripped = stripped[start : end + 1]

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise OcrRuntimeError(f"OCR JSON 파싱에 실패했습니다: {exc}") from exc
    if not isinstance(parsed, dict):
        raise OcrRuntimeError("OCR 응답 JSON이 객체 형식이 아닙니다.")
    return parsed


def _find_field_value(data: Any, field: str, raw_fields: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    candidates = _collect_candidate_pairs(data)
    raw_text = _raw_text_from_fields(raw_fields)
    if raw_text:
        candidates.extend(_line_candidates(raw_text))

    best: tuple[float, Any, str] | None = None
    for label, value in candidates:
        score = _label_match_score(field, label)
        if score <= 0:
            continue

        candidate_value = _extract_value_from_candidate(field, value, label)
        if candidate_value is None:
            continue
        if best is None or score > best[0]:
            best = (score, candidate_value, label)

    if best is None and raw_text:
        text_value, label = _find_text_value_by_context(field, raw_text)
        if text_value is not None:
            best = (0.6, text_value, label)

    if best is None:
        return None, {}

    score, value, label = best
    return value, {"matched_label": label, "confidence": round(min(score, 1.0), 2)}


def _collect_candidate_pairs(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        structured_label = _first_key_value(data, STRUCTURED_LABEL_KEYS)
        structured_value = _first_key_value(data, STRUCTURED_VALUE_KEYS)
        if structured_label is not None and structured_value is not None:
            pairs.append((str(structured_label), structured_value))

        for key, value in data.items():
            key_text = str(key)
            label = f"{prefix} {key_text}".strip()
            if isinstance(value, (dict, list)):
                pairs.extend(_collect_candidate_pairs(value, label))
            else:
                pairs.append((label, value))
    elif isinstance(data, list):
        for index, item in enumerate(data):
            pairs.extend(_collect_candidate_pairs(item, f"{prefix} {index}".strip()))
    elif isinstance(data, str):
        pairs.extend(_line_candidates(data))
    return pairs


def _first_key_value(data: dict[str, Any], key_set: set[str]) -> Any:
    normalized = {_normalize_key(key): value for key, value in data.items()}
    for key in key_set:
        value = normalized.get(_normalize_key(key))
        if value not in (None, ""):
            return value
    return None


def _line_candidates(text: str) -> list[tuple[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates: list[tuple[str, str]] = []
    for line in lines:
        candidates.append((line, line))
        parts = re.split(r"[:：|]\s*|\s{2,}", line, maxsplit=1)
        if len(parts) == 2:
            candidates.append((parts[0], parts[1]))
    return candidates


def _raw_text_from_fields(raw_fields: dict[str, Any]) -> str:
    raw_values: list[str] = []
    for key in ("raw_text", "ocr_text", "text", "full_text", "recognized_text"):
        value = raw_fields.get(key)
        if isinstance(value, str):
            raw_values.append(value)
    if isinstance(raw_fields.get("pages"), list):
        for page in raw_fields["pages"]:
            if isinstance(page, dict):
                raw_values.append(_raw_text_from_fields(page))
            elif isinstance(page, str):
                raw_values.append(page)
    return "\n".join(value for value in raw_values if value).strip()


def _label_match_score(field: str, label: str) -> float:
    normalized_label = _normalize_key(label)
    if not normalized_label:
        return 0

    best = 0.0
    for alias in FIELD_ALIASES[field]:
        normalized_alias = _normalize_key(alias)
        if not normalized_alias:
            continue
        if normalized_alias == normalized_label:
            best = max(best, 1.0)
        elif normalized_alias in normalized_label:
            best = max(best, 0.92)
        elif normalized_label in normalized_alias:
            best = max(best, 0.85)
        else:
            best = max(best, SequenceMatcher(None, normalized_alias, normalized_label).ratio() * 0.72)

    if field in {"hdl", "ldl"} and _normalize_key(field) not in normalized_label:
        if "콜레스테롤" in label and field == "hdl" and "고밀도" not in label:
            best = min(best, 0.35)
        if "콜레스테롤" in label and field == "ldl" and "저밀도" not in label:
            best = min(best, 0.35)
    if field == "total_cholesterol" and any(token in normalized_label for token in ("hdl", "ldl", "고밀도", "저밀도")):
        return 0
    if field == "fasting_glucose" and ("혈색소" in label or "당화" in label or "hba1c" in normalized_label):
        return 0
    return best if best >= 0.52 else 0


def _extract_value_from_candidate(field: str, value: Any, label: str) -> Any:
    if field in {"systolic_bp", "diastolic_bp"}:
        pair = _extract_bp_pair(str(value))
        if pair:
            return pair[0] if field == "systolic_bp" else pair[1]
        pair = _extract_bp_pair(label)
        if pair:
            return pair[0] if field == "systolic_bp" else pair[1]
    return value


def _find_text_value_by_context(field: str, text: str) -> tuple[Any, str]:
    for line in text.splitlines():
        if _label_match_score(field, line) <= 0:
            continue
        if field in {"systolic_bp", "diastolic_bp"}:
            pair = _extract_bp_pair(line)
            if pair:
                return (pair[0] if field == "systolic_bp" else pair[1]), line
        for number in _numbers_from_text(line):
            if _coerce_numeric(field, number) is not None:
                return number, line
    return None, ""


def _extract_bp_pair(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    if not any(keyword in text for keyword in ("혈압", "bp", "BP", "수축", "이완", "최고", "최저")):
        return None
    numbers = [int(round(float(number))) for number in _numbers_from_text(text)]
    numbers = [number for number in numbers if 40 <= number <= 240]
    if len(numbers) >= 2:
        high, low = numbers[0], numbers[1]
        return (max(high, low), min(high, low))
    return None


def _numbers_from_text(text: str) -> list[float]:
    return [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))]


def _normalize_key(value: str) -> str:
    return re.sub(r"[\s_()\-./]+", "", value).lower()


def _normalize_sex(value: Any) -> str | None:
    text = str(value).strip().lower()
    if text in {"male", "m", "남", "남성", "1"}:
        return "male"
    if text in {"female", "f", "여", "여성", "2"}:
        return "female"
    return None


def _coerce_numeric(field: str, value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
        if not match:
            return None
        number = float(match.group(0))

    minimum, maximum, caster = NUMERIC_RANGES[field]
    if not minimum <= number <= maximum:
        return None
    if caster is int:
        return int(round(number))
    return round(number, 1)


def _short_error(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:300] if cleaned else "empty response"
