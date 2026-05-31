"""Central configuration for the knowledge preprocessing pipeline."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    chunk_size: int = 600
    chunk_overlap: int = 80
    min_chunk_chars: int = 50
    min_content_chars: int = 100
    embedding_batch_size: int = 10
    checkpoint_path: Path = Path("data/checkpoints/preprocess_checkpoint.json")
    report_dir: Path = Path("data/reports")
    required_metadata_fields: tuple[str, ...] = (
        "source",
        "title",
        "url",
        "publish_date",
        "region",
        "priority",
        "topic",
    )


PIPELINE_CONFIG = PipelineConfig()
