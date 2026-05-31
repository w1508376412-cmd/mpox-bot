"""Shared helpers for parsing, validating, and chunking raw knowledge files."""
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List
import hashlib
import re

from pipeline_config import PIPELINE_CONFIG, PipelineConfig

MPOX_TERMS = ("猴痘", "mpox", "monkeypox", "MPXV")

NON_MPOX_DISEASE_TERMS = (
    "疟疾",
    "麻疹",
    "狂犬病",
    "发热伴血小板减少综合征",
    "登革热",
    "基孔肯雅热",
    "寨卡",
    "乙脑",
)

FOOTER_PATTERNS = (
    "责任编辑",
    "编辑：",
    "作者：",
    "审核：",
    "监制：",
    "打印本页",
    "关闭窗口",
    "上一篇",
    "下一篇",
)

KNOWN_METADATA_BY_FILE = {
    "nhc_mpox_guideline_2022.txt": {
        "source": "国家卫健委",
        "title": "猴痘防控技术指南（2022年版）",
        "document_id": "猴痘防控技术指南（2022年版）",
        "url": "https://www.nhc.gov.cn/yjb/c100058/202207/fdaf10006d0b4034bca46a28b5f0bd20.shtml",
        "publish_date": "2022-07-01",
        "region": "中国",
        "priority": 1,
    },
    "nhc_mpox_guideline_2022_full.txt": {
        "source": "国家卫健委",
        "title": "猴痘防控技术指南（2022年版）",
        "document_id": "猴痘防控技术指南（2022年版）",
        "url": "https://www.nhc.gov.cn/yjb/c100058/202207/fdaf10006d0b4034bca46a28b5f0bd20.shtml",
        "publish_date": "2022-07-01",
        "region": "中国",
        "priority": 1,
    },
    "ndcpa_mpox_protocol_2023.txt": {
        "title": "猴痘防控方案",
        "document_id": "猴痘防控方案",
        "url": "https://www.ndcpa.gov.cn/jbkzzx/c100014/common/content/content_1698984403881291776.html",
        "publish_date": "2023-07-26",
        "region": "中国",
        "priority": 1,
    },
    "ndcpa_mpox_science_2024.txt": {
        "url": "https://www.ndcpa.gov.cn/jbkzzx/c100040/common/content/content_1834833947705323520.html",
        "region": "中国",
        "priority": 1,
    },
    "who_global_trends_may_2026.txt": {
        "source": "WHO",
        "url": "https://worldhealthorg.shinyapps.io/mpx_global/",
        "region": "global",
        "priority": 2,
    },
    "who_mpx_global_data_2026.txt": {
        "source": "WHO",
        "url": "https://worldhealthorg.shinyapps.io/mpx_global/",
        "region": "global",
        "priority": 2,
    },
    "who_mpox_fact_sheet.txt": {
        "source": "WHO",
        "url": "https://www.who.int/news-room/fact-sheets/detail/mpox",
        "publish_date": "2024-08-26",
        "region": "global",
        "priority": 2,
    },
    "who_mpox_qa.txt": {
        "source": "WHO",
        "url": "https://www.who.int/news-room/questions-and-answers/item/monkeypox",
        "publish_date": "2024-10-16",
        "region": "global",
        "priority": 2,
    },
}

SUPERSEDED_RAW_FILES = {
    "nhc_mpox_guideline_2022.txt",
    "nhc_mpox_guideline_2022_full.txt",
    "ndcpa_mpox_protocol_2023.txt",
}


def is_superseded_raw_file(file_path: Path) -> bool:
    """Return whether a raw file is replaced by a preferred canonical source."""
    return Path(file_path).name in SUPERSEDED_RAW_FILES


SOURCE_ALIASES = {
    "国家卫生健康委": "国家卫健委",
    "国家卫生健康委员会": "国家卫健委",
    "卫生应急办公室": "国家卫健委",
}


@dataclass(frozen=True)
class RawDocument:
    metadata: Dict[str, Any]
    content: str


@dataclass(frozen=True)
class QualityResult:
    passed: bool
    score: float
    warnings: List[str]
    metrics: Dict[str, Any]


def generate_file_fingerprint(file_path: Path) -> str:
    """Generate a stable fingerprint for checkpointing a source file."""
    file_path = Path(file_path)
    stats = file_path.stat()
    payload = f"{file_path.resolve()}|{stats.st_size}|{stats.st_mtime_ns}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def parse_raw_file(file_path: Path) -> RawDocument:
    """Parse a metadata-prefixed raw text file from data/raw."""
    file_path = Path(file_path)
    raw_text = file_path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()
    metadata: Dict[str, Any] = {}
    content_start = 0

    metadata_map = {
        "来源：": "source",
        "标题：": "title",
        "URL：": "url",
        "发布日期：": "publish_date",
        "地区：": "region",
        "优先级：": "priority",
        "主题：": "topic",
    }

    for index, line in enumerate(lines):
        stripped = line.strip()
        if "=" * 50 in stripped:
            content_start = index + 1
            break

        for prefix, key in metadata_map.items():
            if stripped.startswith(prefix):
                value = stripped.replace(prefix, "", 1).strip()
                if key == "priority":
                    metadata[key] = int(value) if value.isdigit() else 2
                elif key == "topic":
                    metadata[key] = [item.strip() for item in value.split(",") if item.strip()]
                elif key == "publish_date":
                    metadata[key] = normalize_publish_date(value)
                else:
                    metadata[key] = value
                break

    content = "\n".join(lines[content_start:]).strip()
    metadata.setdefault("source", "Unknown")
    metadata.setdefault("title", file_path.stem)
    metadata.setdefault("url", "")
    metadata.setdefault("publish_date", "")
    metadata.setdefault("region", "global")
    metadata.setdefault("priority", 2)
    metadata.setdefault("topic", [])
    infer_missing_metadata(file_path, lines, metadata)
    normalize_metadata(file_path, metadata)
    content = clean_document_content(metadata, content)
    metadata["document_id"] = metadata.get("id") or metadata["title"]
    metadata["original_file"] = str(file_path)
    metadata["file_fingerprint"] = generate_file_fingerprint(file_path)

    return RawDocument(metadata=metadata, content=content)


def infer_missing_metadata(file_path: Path, lines: List[str], metadata: Dict[str, Any]) -> None:
    """Infer common metadata for raw files that do not have a standard header block."""
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    if metadata.get("title") == file_path.stem and non_empty_lines:
        metadata["title"] = non_empty_lines[0]

    for line in non_empty_lines[:10]:
        if line.startswith("发布部门：") and metadata.get("source") == "Unknown":
            metadata["source"] = line.replace("发布部门：", "", 1).strip()
        elif line.startswith("发布时间：") and not metadata.get("publish_date"):
            metadata["publish_date"] = normalize_publish_date(line.replace("发布时间：", "", 1).strip())
            metadata["date_source"] = "raw_publish_date"
            metadata["date_confidence"] = "high"
        elif line.startswith("作者：") and metadata.get("source") == "Unknown":
            author = line.replace("作者：", "", 1).strip()
            if "WHO" in author or "World Health Organization" in author:
                metadata["source"] = "WHO"

    parent_name = file_path.parent.name.lower()
    if metadata.get("source") == "Unknown":
        source_by_dir = {
            "china_ndcpa": "国家疾控局",
            "china_nhc": "国家卫健委",
            "china_gov": "国家卫健委",
            "who": "WHO",
            "ecdc": "ECDC",
            "africa_cdc": "Africa CDC",
        }
        metadata["source"] = source_by_dir.get(parent_name, "Unknown")

    if not metadata.get("topic"):
        metadata["topic"] = ["猴痘"]

    if metadata.get("publish_date"):
        metadata.setdefault("date_source", "raw_publish_date")
        metadata.setdefault("date_confidence", "high")


def normalize_metadata(file_path: Path, metadata: Dict[str, Any]) -> None:
    """Normalize source taxonomy, region, URL provenance, and date provenance."""
    known = KNOWN_METADATA_BY_FILE.get(Path(file_path).name, {})
    filled_from_known: set[str] = set()
    for key, value in known.items():
        if key in {"url", "publish_date"}:
            if not metadata.get(key):
                metadata[key] = value
                filled_from_known.add(key)
        elif key in {"title", "document_id"}:
            original_key = f"source_original_{key}"
            if metadata.get(key) and metadata.get(key) != value:
                metadata.setdefault(original_key, metadata[key])
            metadata[key] = value
            filled_from_known.add(key)
        elif metadata.get(key) in (None, "", "Unknown", "global") or key == "priority":
            metadata[key] = value
            filled_from_known.add(key)

    original_source = metadata.get("source", "Unknown").strip()
    if "、" in original_source:
        source_orgs = [SOURCE_ALIASES.get(item.strip(), item.strip()) for item in original_source.split("、") if item.strip()]
    else:
        source_orgs = [SOURCE_ALIASES.get(original_source, original_source)]

    if "国家疾控局" in source_orgs:
        primary = "国家疾控局"
    elif "国家卫健委" in source_orgs:
        primary = "国家卫健委"
    else:
        primary = source_orgs[0] if source_orgs else "Unknown"

    metadata["source_original"] = original_source
    metadata["source"] = primary
    metadata["source_primary"] = primary
    metadata["source_orgs"] = source_orgs
    metadata["source_department"] = "卫生应急办公室" if original_source == "卫生应急办公室" else ""

    if primary in {"国家疾控局", "国家卫健委", "中国疾控中心"}:
        metadata["region"] = "中国"
        metadata["priority"] = 1
    elif primary == "Africa CDC":
        metadata["region"] = "非洲"
        metadata["priority"] = 3
    elif primary == "ECDC":
        metadata["region"] = "欧洲"
    elif primary == "WHO":
        metadata["region"] = "global"

    if metadata.get("publish_date"):
        metadata["publish_date"] = normalize_publish_date(metadata["publish_date"])
        if "publish_date" in filled_from_known:
            metadata["date_source"] = "known_metadata"
            metadata["date_confidence"] = "medium"
        else:
            metadata.setdefault("date_source", "raw_publish_date")
            metadata.setdefault("date_confidence", "high")
    else:
        metadata["publish_date"] = "1970-01-01"
        metadata["date_source"] = "unknown"
        metadata["date_confidence"] = "low"

    if metadata.get("url"):
        metadata["url_status"] = "present"
        metadata["url_missing_reason"] = ""
    else:
        metadata["url_status"] = "missing"
        metadata["url_missing_reason"] = "raw_source_has_no_url"


def has_mpox_keyword(text: str) -> bool:
    """Return whether a string contains mpox-specific terminology."""
    lower_text = text.lower()
    return any(term.lower() in lower_text for term in MPOX_TERMS)


def clean_document_content(metadata: Dict[str, Any], content: str) -> str:
    """Remove obvious non-mpox paragraphs from broad index-like source pages."""
    title = metadata.get("title", "")
    original_file = metadata.get("original_file", "")
    is_broad_china_cdc_page = (
        metadata.get("source") == "中国疾控中心"
        and ("专题" in title or "basic" in original_file or title == "中国疾控中心猴痘专题")
    )
    if not is_broad_china_cdc_page:
        return content.strip()

    kept: List[str] = []
    for paragraph in re.split(r"\n+", content):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if has_mpox_keyword(paragraph):
            kept.append(paragraph)

    return "\n".join(kept).strip()


def strip_footer_tail(content: str) -> str:
    """Remove common author/editor/footer tails near the end of official pages."""
    tail_start = max(len(content) - 360, 0)
    tail = content[tail_start:]
    positions = [
        tail.find(pattern)
        for pattern in ("作者：", "审核：", "编辑：", "监制：", "责任编辑")
        if tail.find(pattern) >= 0
    ]
    if not positions:
        return content.strip()

    cut = tail_start + min(positions)
    return content[:cut].strip()


def normalize_publish_date(value: str) -> str:
    """Normalize common Chinese and ISO-like date strings to YYYY-MM-DD."""
    value = str(value).strip()
    chinese_match = re.match(r"^(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日$", value)
    if chinese_match:
        year, month, day = chinese_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    chinese_month_match = re.match(r"^(\d{4})年\s*(\d{1,2})月$", value)
    if chinese_month_match:
        year, month = chinese_month_match.groups()
        return f"{int(year):04d}-{int(month):02d}-01"

    for date_format in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue

    return value


SECTION_HEADING_RE = re.compile(
    r"^\s*(?:"
    r"[一二三四五六七八九十]+[、.．]\s*.+"
    r"|（[一二三四五六七八九十]+）\s*.+"
    r"|\([一二三四五六七八九十]+\)\s*.+"
    r"|\d+[、.．]\s*[^。；;]{2,80}$"
    r"|[A-Z][A-Za-z /-]{2,80}$"
    r")\s*$"
)

SENTENCE_END_RE = re.compile(r"(?<=[。！？；.!?;])\s*")


def is_section_heading(line: str) -> bool:
    """Detect section titles and numbered headings commonly found in official docs."""
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    return bool(SECTION_HEADING_RE.match(stripped))


def iter_text_blocks(text: str) -> List[Dict[str, Any]]:
    """Return non-empty line blocks with character offsets in the original text."""
    blocks: List[Dict[str, Any]] = []
    cursor = 0
    for raw_line in text.splitlines(keepends=True):
        line_without_newline = raw_line.rstrip("\r\n")
        stripped = line_without_newline.strip()
        line_start = cursor
        cursor += len(raw_line)
        if not stripped:
            continue

        leading = len(line_without_newline) - len(line_without_newline.lstrip())
        trailing = len(line_without_newline.rstrip())
        start = line_start + leading
        end = line_start + trailing
        blocks.append(
            {
                "text": stripped,
                "start_char": start,
                "end_char": end,
                "is_heading": is_section_heading(stripped),
            }
        )
    return blocks


def split_long_block(block: Dict[str, Any], chunk_size: int) -> List[Dict[str, Any]]:
    """Split an overlong paragraph on sentence boundaries without starting mid-sentence."""
    text = block["text"]
    if len(text) <= chunk_size:
        return [block]

    parts: List[Dict[str, Any]] = []
    sentence_start = 0
    current_sentences: List[tuple[int, str]] = []
    current_len = 0

    for match in SENTENCE_END_RE.finditer(text):
        sentence_end = match.end()
        sentence = text[sentence_start:sentence_end].strip()
        if sentence:
            if current_sentences and current_len + len(sentence) > chunk_size:
                part_start = current_sentences[0][0]
                part_text = "".join(item[1] for item in current_sentences).strip()
                parts.append(
                    {
                        "text": part_text,
                        "start_char": block["start_char"] + part_start,
                        "end_char": block["start_char"] + part_start + len(part_text),
                        "is_heading": False,
                    }
                )
                current_sentences = []
                current_len = 0
            current_sentences.append((sentence_start, sentence))
            current_len += len(sentence)
        sentence_start = sentence_end

    remainder = text[sentence_start:].strip()
    if remainder:
        if current_sentences and current_len + len(remainder) > chunk_size:
            part_start = current_sentences[0][0]
            part_text = "".join(item[1] for item in current_sentences).strip()
            parts.append(
                {
                    "text": part_text,
                    "start_char": block["start_char"] + part_start,
                    "end_char": block["start_char"] + part_start + len(part_text),
                    "is_heading": False,
                }
            )
            current_sentences = []
        current_sentences.append((sentence_start, remainder))

    if current_sentences:
        part_start = current_sentences[0][0]
        part_text = "".join(item[1] for item in current_sentences).strip()
        parts.append(
            {
                "text": part_text,
                "start_char": block["start_char"] + part_start,
                "end_char": block["start_char"] + part_start + len(part_text),
                "is_heading": False,
            }
        )

    return parts or [block]


def chunk_document(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
    min_chunk_chars: int | None = None,
) -> List[Dict[str, Any]]:
    """Split text into section-aware chunks with section titles and char offsets."""
    chunk_size = chunk_size or PIPELINE_CONFIG.chunk_size
    min_chunk_chars = min_chunk_chars or PIPELINE_CONFIG.min_chunk_chars

    if overlap is not None and overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = strip_footer_tail(text.strip())
    blocks = iter_text_blocks(text)
    expanded_blocks: List[Dict[str, Any]] = []
    for block in blocks:
        expanded_blocks.extend(split_long_block(block, chunk_size))

    segments: List[Dict[str, Any]] = []
    current_lines: List[str] = []
    current_start: int | None = None
    current_end: int | None = None
    current_section = ""
    active_section = ""

    def flush() -> None:
        nonlocal current_lines, current_start, current_end, current_section
        if current_start is None or current_end is None:
            return
        content = "\n".join(line for line in current_lines if line.strip()).strip()
        if len(content) >= min_chunk_chars:
            segments.append(
                {
                    "content": content,
                    "section_title": current_section,
                    "start_char": current_start,
                    "end_char": current_end,
                }
            )
        current_lines = []
        current_start = None
        current_end = None

    for block in expanded_blocks:
        block_text = block["text"]
        if any(pattern in block_text for pattern in FOOTER_PATTERNS) and len(block_text) < 180:
            continue

        if block["is_heading"]:
            flush()
            active_section = block_text

        proposed_lines = current_lines + [block_text]
        proposed = "\n".join(proposed_lines).strip()
        if current_lines and len(proposed) > chunk_size:
            flush()
            current_section = active_section
            current_lines = [active_section, block_text] if active_section and block_text != active_section else [block_text]
            current_start = block["start_char"] if not active_section else min(block["start_char"], block["start_char"])
            current_end = block["end_char"]
            continue

        if not current_lines:
            current_section = active_section if active_section else (block_text if block["is_heading"] else "")
            current_start = block["start_char"]
        current_lines.append(block_text)
        current_end = block["end_char"]

    flush()
    return segments


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
    min_chunk_chars: int | None = None,
) -> List[str]:
    """Compatibility wrapper returning only chunk text."""
    return [
        segment["content"]
        for segment in chunk_document(
            text,
            chunk_size=chunk_size,
            overlap=overlap,
            min_chunk_chars=min_chunk_chars,
        )
    ]


def validate_document(
    metadata: Dict[str, Any],
    content: str,
    config: PipelineConfig = PIPELINE_CONFIG,
) -> QualityResult:
    """Validate raw document quality before generating embeddings."""
    warnings: List[str] = []
    missing = [field for field in config.required_metadata_fields if not metadata.get(field)]
    if missing:
        warnings.append(f"缺少元数据字段: {', '.join(missing)}")

    content_length = len(content.strip())
    if content_length < config.min_content_chars:
        warnings.append(f"正文过短: {content_length} 字符")

    if not has_mpox_keyword(content):
        warnings.append("正文未发现猴痘/mpox/monkeypox关键词")

    if has_non_mpox_contamination(content):
        warnings.append("疑似混入非猴痘主题内容")

    score = 1.0
    score -= min(len(missing) * 0.1, 0.4)
    if content_length < config.min_content_chars:
        score -= 0.4
    if any(warning.startswith("正文未发现") for warning in warnings):
        score -= 0.1
    if any(warning == "疑似混入非猴痘主题内容" for warning in warnings):
        score -= 0.2

    score = max(round(score, 2), 0.0)
    passed = content_length >= config.min_content_chars and len(missing) <= 2

    return QualityResult(
        passed=passed,
        score=score,
        warnings=warnings,
        metrics={
            "content_length": content_length,
            "missing_metadata": missing,
            "has_mpox_keyword": has_mpox_keyword(content),
            "has_non_mpox_contamination": has_non_mpox_contamination(content),
        },
    )


def has_non_mpox_contamination(text: str) -> bool:
    """Flag chunks that mention unrelated disease terms without mpox context."""
    lower_text = text.lower()
    return any(term.lower() in lower_text for term in NON_MPOX_DISEASE_TERMS) and not has_mpox_keyword(text)


def assess_chunk_quality(content: str) -> Dict[str, Any]:
    """Create retrieval-facing quality metadata for one chunk."""
    stripped = content.strip()
    contains_mpox = has_mpox_keyword(stripped)
    is_footer_like = any(pattern in stripped for pattern in FOOTER_PATTERNS)
    is_short = len(stripped) < PIPELINE_CONFIG.min_chunk_chars
    is_suspected_irrelevant = has_non_mpox_contamination(stripped)

    warnings: List[str] = []
    score = 1.0
    if not contains_mpox:
        score -= 0.1
    if is_footer_like:
        warnings.append("疑似页脚或编辑信息")
        score -= 0.45
    if is_short:
        warnings.append("chunk过短")
        score -= 0.25
    if is_suspected_irrelevant:
        warnings.append("疑似非猴痘主题")
        score -= 0.5

    return {
        "quality_score": max(round(score, 2), 0.0),
        "quality_warnings": warnings,
        "contains_mpox_keyword": contains_mpox,
        "is_footer_like": is_footer_like,
        "is_suspected_irrelevant": is_suspected_irrelevant,
        "language": "zh" if re.search(r"[\u4e00-\u9fff]", stripped) else "en",
    }


def create_chunk_records(metadata: Dict[str, Any], chunks: List[Any]) -> List[Dict[str, Any]]:
    """Create deterministic chunk records for database upsert."""
    records: List[Dict[str, Any]] = []
    document_id = metadata.get("document_id") or metadata.get("title") or "unknown"

    for index, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            content = chunk["content"]
            section_title = chunk.get("section_title", "")
            start_char = chunk.get("start_char")
            end_char = chunk.get("end_char")
        else:
            content = chunk
            section_title = ""
            start_char = None
            end_char = None
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:24]
        chunk_hash = hashlib.sha256(f"{document_id}|{index}|{content}".encode("utf-8")).hexdigest()[:24]
        quality = assess_chunk_quality(content)
        records.append(
            {
                "id": f"{document_id}-{chunk_hash}",
                "document_id": document_id,
                "content": content,
                "content_preview": content[:180],
                "content_hash": content_hash,
                "section_title": section_title,
                "start_char": start_char,
                "end_char": end_char,
                "metadata": metadata,
                "quality": quality,
                "chunk_index": index,
            }
        )

    return records
