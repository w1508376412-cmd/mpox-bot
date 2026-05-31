"""Static regression checks for the RAG data pipeline configuration."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class PipelineConsistencyTest(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_docs_and_compose_use_alibaba_embedding_defaults(self):
        for relative_path in ("init_db.sql", "docker-compose.yml", ".env.example"):
            with self.subTest(file=relative_path):
                content = self.read(relative_path)
                self.assertNotIn("text-embedding-3-small", content)
                self.assertNotIn("OpenAI text-embedding", content)

        self.assertIn("text-embedding-v4", self.read("docker-compose.yml"))
        self.assertIn("ALIBABA_API_BASE", self.read(".env.example"))
        self.assertIn("embedding vector(1024)", self.read("init_db.sql"))

    def test_embedding_generation_paths_write_pgvector_column(self):
        for relative_path in (
            "backend/process_data_real.py",
            "backend/process_official_docx.py",
            "backend/process_dashboard_data.py",
        ):
            with self.subTest(file=relative_path):
                content = self.read(relative_path)
                self.assertIn("embedding, embedding_json", content)

    def test_retriever_uses_runtime_date_for_recency_weight(self):
        content = self.read("backend/retriever_vector.py")
        self.assertNotIn("datetime.date(2026, 5, 18)", content)
        self.assertIn("datetime.date.today()", content)

    def test_frontend_has_no_word_export_state(self):
        frontend = self.read("frontend/index.html")
        self.assertNotIn("lastAnswerData", frontend)
        self.assertNotIn("dataset.answer", frontend)
        self.assertNotIn("/export-word", frontend)

        backend = self.read("backend/main.py")
        self.assertIn('@app.post("/export-word")', backend)

    def test_process_data_real_uses_shared_preprocessing_modules(self):
        content = self.read("backend/process_data_real.py")
        self.assertIn("from checkpoint_manager import CheckpointManager", content)
        self.assertIn("from pipeline_config import PIPELINE_CONFIG", content)
        self.assertIn("from preprocess_utils import", content)
        self.assertNotIn("def chunk_text(", content)
        self.assertNotIn("def parse_raw_file(", content)

    def test_reference_sources_are_limited_to_two_at_api_and_frontend_boundaries(self):
        backend = self.read("backend/main.py")
        frontend = self.read("frontend/index.html")

        self.assertIn("select_reference_sources(sources)", backend)
        self.assertIn("select_reference_sources(request.sources)", backend)
        self.assertIn("data.sources.slice(0, 2)", frontend)

    def test_frontend_keeps_viewport_at_new_question_while_answer_is_appended(self):
        frontend = self.read("frontend/index.html")

        self.assertIn("overflow-anchor: none", frontend)
        self.assertIn("const questionMessage = addUserMessage(question)", frontend)
        self.assertIn("displayAnswer(data, question, questionMessage)", frontend)
        self.assertIn("scrollQuestionIntoView(questionMessage)", frontend)
        self.assertNotIn("chatArea.appendChild(div);\n            scrollQuestionIntoView(div);", frontend)
        self.assertNotIn("chatArea.scrollTop = chatArea.scrollHeight", frontend)


if __name__ == "__main__":
    unittest.main()
