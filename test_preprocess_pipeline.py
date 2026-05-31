"""Tests for the lightweight knowledge preprocessing pipeline."""
from pathlib import Path
import json
import tempfile
import unittest
import sys


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


class PreprocessPipelineTest(unittest.TestCase):
    def test_config_has_single_source_of_truth_for_chunking(self):
        from pipeline_config import PIPELINE_CONFIG

        self.assertEqual(PIPELINE_CONFIG.chunk_size, 600)
        self.assertEqual(PIPELINE_CONFIG.chunk_overlap, 80)
        self.assertEqual(PIPELINE_CONFIG.embedding_batch_size, 10)
        self.assertEqual(PIPELINE_CONFIG.min_content_chars, 100)

    def test_parse_validate_and_chunk_raw_file(self):
        from preprocess_utils import chunk_text, parse_raw_file, validate_document

        body = "猴痘是什么。猴痘主要通过密切接触传播。" * 20

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_file = Path(tmpdir) / "sample.txt"
            raw_file.write_text(
                "\n".join(
                    [
                        "来源：中国疾控中心",
                        "标题：猴痘防控知识问答",
                        "URL：https://example.com/mpox",
                        "发布日期：2025-01-09",
                        "地区：中国",
                        "优先级：1",
                        "主题：症状, 传播, 预防",
                        "=" * 80,
                        body,
                    ]
                ),
                encoding="utf-8",
            )

            parsed = parse_raw_file(raw_file)

        self.assertEqual(parsed.metadata["source"], "中国疾控中心")
        self.assertEqual(parsed.metadata["priority"], 1)
        self.assertEqual(parsed.metadata["topic"], ["症状", "传播", "预防"])
        self.assertEqual(parsed.metadata["document_id"], "猴痘防控知识问答")
        self.assertEqual(parsed.content, body)

        quality = validate_document(parsed.metadata, parsed.content)
        self.assertTrue(quality.passed)
        self.assertGreaterEqual(quality.score, 0.8)
        self.assertEqual(quality.warnings, [])

        chunks = chunk_text(parsed.content, chunk_size=80, overlap=10)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) > 30 for chunk in chunks))

    def test_parse_raw_file_normalizes_chinese_publish_date(self):
        from preprocess_utils import parse_raw_file

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_file = Path(tmpdir) / "sample.txt"
            raw_file.write_text(
                "\n".join(
                    [
                        "来源：WHO",
                        "标题：全球猴痘趋势",
                        "URL：https://example.com",
                        "发布日期：2026年5月8日",
                        "地区：global",
                        "优先级：2",
                        "主题：疫情",
                        "=" * 80,
                        "mpox global update " * 20,
                    ]
                ),
                encoding="utf-8",
            )

            parsed = parse_raw_file(raw_file)

        self.assertEqual(parsed.metadata["publish_date"], "2026-05-08")

    def test_parse_raw_file_infers_metadata_without_header_block(self):
        from preprocess_utils import parse_raw_file

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "data" / "raw" / "china_ndcpa"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "ndcpa_mpox_science_2024.txt"
            raw_file.write_text(
                "\n".join(
                    [
                        "猴痘防控科普知识 (2024年版)",
                        "发布部门：国家疾控局",
                        "发布时间：2024年9月",
                        "",
                        "一、什么是猴痘？",
                        "猴痘是由猴痘病毒感染所致的一种人畜共患病。",
                    ]
                ),
                encoding="utf-8",
            )

            parsed = parse_raw_file(raw_file)

        self.assertEqual(parsed.metadata["source"], "国家疾控局")
        self.assertEqual(parsed.metadata["title"], "猴痘防控科普知识 (2024年版)")
        self.assertEqual(parsed.metadata["publish_date"], "2024-09-01")
        self.assertEqual(parsed.metadata["region"], "中国")
        self.assertEqual(parsed.metadata["priority"], 1)

    def test_broad_china_cdc_topic_page_keeps_only_mpox_paragraphs(self):
        from preprocess_utils import parse_raw_file, validate_document

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "data" / "raw" / "中国疾控中心"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "china_cdc_mpox_basic.txt"
            raw_file.write_text(
                "\n".join(
                    [
                        "来源：中国疾控中心",
                        "标题：中国疾控中心猴痘专题",
                        "URL：https://www.chinacdc.cn/jkkp/crb/ycr/",
                        "发布日期：2024-12-01",
                        "地区：中国",
                        "优先级：1",
                        "主题：猴痘",
                        "=" * 80,
                        "2026年全国疟疾宣传日--回国就医时主动告知旅行史。",
                        "狂犬病是由狂犬病病毒引起的人畜共患传染病。",
                        "猴痘（Mpox）是一种由猴痘病毒（Monkeypox virus, MPXV）引起的传染病。",
                        "猴痘主要通过密切接触传播，出现发热、皮疹、淋巴结肿大等症状应及时就医。密切接触者应进行21天健康监测，并避免与他人发生密切接触。",
                    ]
                ),
                encoding="utf-8",
            )

            parsed = parse_raw_file(raw_file)

        self.assertIn("猴痘（Mpox）", parsed.content)
        self.assertIn("密切接触传播", parsed.content)
        self.assertNotIn("疟疾宣传日", parsed.content)
        self.assertNotIn("狂犬病病毒", parsed.content)

        quality = validate_document(parsed.metadata, parsed.content)
        self.assertTrue(quality.passed)
        self.assertNotIn("疑似混入非猴痘主题内容", quality.warnings)

    def test_metadata_normalization_records_provenance_and_source_taxonomy(self):
        from preprocess_utils import parse_raw_file

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "data" / "raw" / "china_ndcpa"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "ndcpa_mpox_protocol_2023.txt"
            raw_file.write_text(
                "\n".join(
                    [
                        "猴痘防控方案 (2023年版)",
                        "发布部门：国家疾控局、国家卫生健康委",
                        "发布时间：2023年7月26日",
                        "",
                        "猴痘防控方案用于指导疫情监测、病例发现和处置。",
                    ]
                ),
                encoding="utf-8",
            )

            parsed = parse_raw_file(raw_file)

        self.assertEqual(parsed.metadata["source"], "国家疾控局")
        self.assertEqual(parsed.metadata["title"], "猴痘防控方案")
        self.assertEqual(parsed.metadata["document_id"], "猴痘防控方案")
        self.assertEqual(parsed.metadata["source_original_title"], "猴痘防控方案 (2023年版)")
        self.assertEqual(parsed.metadata["source_primary"], "国家疾控局")
        self.assertEqual(parsed.metadata["source_orgs"], ["国家疾控局", "国家卫健委"])
        self.assertEqual(parsed.metadata["region"], "中国")
        self.assertEqual(parsed.metadata["date_source"], "raw_publish_date")
        self.assertEqual(parsed.metadata["date_confidence"], "high")
        self.assertEqual(parsed.metadata["url_status"], "present")
        self.assertEqual(parsed.metadata["url_missing_reason"], "")

    def test_nhc_technical_guide_notification_alias_keeps_preferred_document_id(self):
        from preprocess_utils import parse_raw_file

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "data" / "raw" / "china_nhc"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "nhc_mpox_guideline_2022_full.txt"
            raw_file.write_text(
                "\n".join(
                    [
                        "国家卫生健康委办公厅关于印发猴痘防控技术指南（2022年版）的通知",
                        "国卫办应急函〔2022〕221号",
                        "",
                        "一、背景",
                        "猴痘是一种由猴痘病毒感染所致的人兽共患病毒性疾病。",
                        "本指南用于指导猴痘疫情防控技术工作。",
                    ]
                ),
                encoding="utf-8",
            )

            parsed = parse_raw_file(raw_file)

        self.assertEqual(parsed.metadata["title"], "猴痘防控技术指南（2022年版）")
        self.assertEqual(parsed.metadata["document_id"], "猴痘防控技术指南（2022年版）")
        self.assertEqual(parsed.metadata["source_original_title"], "国家卫生健康委办公厅关于印发猴痘防控技术指南（2022年版）的通知")
        self.assertEqual(parsed.metadata["url_status"], "present")
        self.assertEqual(parsed.metadata["publish_date"], "2022-07-01")

    def test_collect_raw_files_skips_superseded_nhc_notification_files(self):
        from preprocess_utils import is_superseded_raw_file

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "data" / "raw"
            duplicate_dir = raw_dir / "china_nhc"
            preferred_dir = raw_dir / "国家卫健委"
            duplicate_dir.mkdir(parents=True)
            preferred_dir.mkdir(parents=True)
            (duplicate_dir / "nhc_mpox_guideline_2022.txt").write_text("duplicate", encoding="utf-8")
            (duplicate_dir / "nhc_mpox_guideline_2022_full.txt").write_text("duplicate", encoding="utf-8")
            preferred = preferred_dir / "nhc_mpox_technical_guide_2022.txt"
            preferred.write_text("preferred", encoding="utf-8")

            self.assertTrue(is_superseded_raw_file(duplicate_dir / "nhc_mpox_guideline_2022.txt"))
            self.assertTrue(is_superseded_raw_file(duplicate_dir / "nhc_mpox_guideline_2022_full.txt"))
            self.assertFalse(is_superseded_raw_file(preferred))

    def test_ndcpa_2023_protocol_is_superseded_by_preferred_prevention_plan(self):
        from preprocess_utils import is_superseded_raw_file, parse_raw_file

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "data" / "raw" / "china_ndcpa"
            raw_dir.mkdir(parents=True)
            raw_file = raw_dir / "ndcpa_mpox_protocol_2023.txt"
            raw_file.write_text(
                "\n".join(
                    [
                        "猴痘防控方案 (2023年版)",
                        "发布部门：国家疾控局、国家卫生健康委",
                        "发布时间：2023年7月26日",
                        "",
                        "猴痘防控方案用于指导疫情监测、病例发现和处置。",
                    ]
                ),
                encoding="utf-8",
            )

            parsed = parse_raw_file(raw_file)

        self.assertTrue(is_superseded_raw_file(raw_file))
        self.assertEqual(parsed.metadata["title"], "猴痘防控方案")
        self.assertEqual(parsed.metadata["document_id"], "猴痘防控方案")
        self.assertEqual(parsed.metadata["source_original_title"], "猴痘防控方案 (2023年版)")

    def test_who_pheic_status_update_uses_2025_end_date_and_continued_controls(self):
        from preprocess_utils import parse_raw_file

        raw_file = ROOT / "data" / "raw" / "who" / "who_mpox_pheic_status_2025.txt"
        parsed = parse_raw_file(raw_file)

        self.assertEqual(parsed.metadata["source"], "WHO")
        self.assertEqual(parsed.metadata["publish_date"], "2025-10-30")
        self.assertIn("2025年9月5日", parsed.content)
        self.assertIn("不再构成", parsed.content)
        self.assertIn("解除PHEIC不意味着猴痘威胁已经消失", parsed.content)
        self.assertIn("2026年8月20日", parsed.content)

    def test_chunk_records_include_quality_fields_and_preview(self):
        from preprocess_utils import create_chunk_records

        metadata = {
            "document_id": "doc-1",
            "title": "猴痘防控知识",
            "source": "国家疾控局",
            "topic": ["猴痘"],
        }
        chunks = [
            "猴痘主要通过密切接触传播，出现皮疹、发热、淋巴结肿大等症状应及时就医。",
            "责任编辑：张三",
        ]

        records = create_chunk_records(metadata, chunks)

        self.assertTrue(records[0]["quality"]["contains_mpox_keyword"])
        self.assertFalse(records[0]["quality"]["is_footer_like"])
        self.assertEqual(records[0]["content_preview"], chunks[0])
        self.assertIn("content_hash", records[0])
        self.assertTrue(records[1]["quality"]["is_footer_like"])
        self.assertLess(records[1]["quality"]["quality_score"], records[0]["quality"]["quality_score"])

    def test_structure_aware_chunking_preserves_sections_and_offsets(self):
        from preprocess_utils import chunk_document

        text = "\n".join(
            [
                "一、传播途径",
                "1. 直接接触：猴痘主要通过直接接触患者皮疹、体液或污染物传播。",
                "2. 间接接触：接触被病毒污染的衣物、床单等物品也可能感染。",
                "",
                "二、就医建议",
                "怀疑感染猴痘时，应尽快到医疗机构就诊，并主动告知可疑接触史。",
            ]
        )

        segments = chunk_document(text, chunk_size=90, overlap=0, min_chunk_chars=20)

        self.assertGreaterEqual(len(segments), 2)
        self.assertEqual(segments[0]["section_title"], "一、传播途径")
        self.assertEqual(segments[-1]["section_title"], "二、就医建议")
        self.assertTrue(all(segment["start_char"] >= 0 for segment in segments))
        self.assertTrue(all(segment["end_char"] > segment["start_char"] for segment in segments))
        self.assertTrue(all(not segment["content"].startswith("传播。") for segment in segments))
        self.assertTrue(any(segment["content"].startswith("一、传播途径") for segment in segments))
        self.assertTrue(any(segment["content"].startswith("二、就医建议") for segment in segments))

    def test_chunk_records_keep_section_title_and_char_offsets(self):
        from preprocess_utils import create_chunk_records

        metadata = {
            "document_id": "doc-2",
            "title": "猴痘防控知识",
            "source": "国家疾控局",
            "topic": ["猴痘"],
        }
        segments = [
            {
                "content": "一、传播途径\n猴痘主要通过密切接触传播。",
                "section_title": "一、传播途径",
                "start_char": 0,
                "end_char": 23,
            }
        ]

        records = create_chunk_records(metadata, segments)

        self.assertEqual(records[0]["section_title"], "一、传播途径")
        self.assertEqual(records[0]["start_char"], 0)
        self.assertEqual(records[0]["end_char"], 23)

    def test_checkpoint_records_success_and_failure(self):
        from checkpoint_manager import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "preprocess_checkpoint.json"
            raw_file = Path(tmpdir) / "source.txt"
            raw_file.write_text("猴痘知识", encoding="utf-8")

            manager = CheckpointManager(checkpoint_path)
            self.assertFalse(manager.is_processed(raw_file))

            manager.record_success(raw_file, {"chunks": 3, "quality_score": 1.0})
            self.assertTrue(manager.is_processed(raw_file))

            failed_file = Path(tmpdir) / "failed.txt"
            failed_file.write_text("bad", encoding="utf-8")
            manager.record_failure(failed_file, "too short")

            stored = json.loads(checkpoint_path.read_text(encoding="utf-8"))

        self.assertEqual(len(stored["processed"]), 1)
        self.assertEqual(len(stored["failed"]), 1)
        self.assertEqual(stored["summary"]["total_successful"], 1)
        self.assertEqual(stored["summary"]["total_failed"], 1)


if __name__ == "__main__":
    unittest.main()
