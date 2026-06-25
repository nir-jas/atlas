from __future__ import annotations

# ruff: noqa: E402
import argparse
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
API_SRC_DIR = ROOT_DIR / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC_DIR))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from atlas_api.core.config import settings
from atlas_api.core.dependencies import (
    get_embedding_provider,
    get_llm_provider,
    get_upload_dir,
)
from atlas_api.db.base import Base
from atlas_api.db.session import get_session
from atlas_api.embedding_providers.fake import FakeEmbeddingProvider
from atlas_api.llm_providers.fake import FakeLLMProvider
from atlas_api.main import create_app
from atlas_api.models import Chunk, ChunkEmbedding, Document
from atlas_api.services.answer_generation import INSUFFICIENT_CONTEXT_ANSWER

_ = (Chunk, ChunkEmbedding, Document)

DEFAULT_CASES_PATH = ROOT_DIR / "evals" / "rag_cases.json"


@dataclass(frozen=True)
class CaseResult:
    name: str
    passed: bool
    source_passed: bool
    answer_passed: bool
    no_context_passed: bool | None
    expected_sources: list[str]
    actual_sources: list[str]
    missing_phrases: list[str]
    answer: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Atlas RAG eval cases with fake providers.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help=f"Path to eval case JSON. Defaults to {DEFAULT_CASES_PATH.relative_to(ROOT_DIR)}.",
    )
    args = parser.parse_args()

    fixture = load_fixture(args.cases)
    documents = require_list(fixture, "documents")
    cases = require_list(fixture, "cases")

    with isolated_fake_client() as client:
        seed_documents(client, documents)
        results = [run_case(client, index, case) for index, case in enumerate(cases, start=1)]

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        no_context = (
            "n/a" if result.no_context_passed is None else pass_fail(result.no_context_passed)
        )
        print(
            f"{status} {result.name} "
            f"(sources={pass_fail(result.source_passed)}, "
            f"answer={pass_fail(result.answer_passed)}, no_context={no_context})"
        )
        if not result.passed:
            print(f"  expected_sources={result.expected_sources}")
            print(f"  actual_sources={result.actual_sources}")
            if result.missing_phrases:
                print(f"  missing_answer_phrases={result.missing_phrases}")
            print(f"  answer={result.answer!r}")

    passed_count = sum(result.passed for result in results)
    total_count = len(results)
    score = passed_count / total_count if total_count else 0
    print(f"Final score: {passed_count}/{total_count} passed ({score:.1%})")

    return 0 if passed_count == total_count else 1


def load_fixture(path: Path) -> dict[str, Any]:
    try:
        raw_fixture = json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"Eval fixture not found: {path}") from None
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error

    if not isinstance(raw_fixture, dict):
        raise SystemExit(f"Eval fixture must be a JSON object: {path}")
    return raw_fixture


def require_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SystemExit(f"Eval fixture field '{key}' must be a list of objects.")
    return value


@contextmanager
def isolated_fake_client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TemporaryDirectory(prefix="atlas-rag-evals-") as upload_dir_name:

        def override_get_session() -> Iterator[Session]:
            with testing_session_local() as session:
                yield session

        def override_get_upload_dir() -> Path:
            return Path(upload_dir_name)

        def override_get_embedding_provider() -> FakeEmbeddingProvider:
            return FakeEmbeddingProvider(dimensions=settings.vector_dimensions)

        def override_get_llm_provider() -> FakeLLMProvider:
            return FakeLLMProvider()

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session
        app.dependency_overrides[get_upload_dir] = override_get_upload_dir
        app.dependency_overrides[get_embedding_provider] = override_get_embedding_provider
        app.dependency_overrides[get_llm_provider] = override_get_llm_provider

        with TestClient(app) as client:
            yield client


def seed_documents(client: TestClient, documents: list[dict[str, Any]]) -> None:
    for index, document in enumerate(documents, start=1):
        filename = require_string(document, "filename", f"documents[{index}]")
        collection = require_string(document, "collection", f"documents[{index}]")
        document_type = str(document.get("document_type", "note"))
        text = require_string(document, "text", f"documents[{index}]")

        response = client.post(
            "/api/v1/documents/upload",
            data={"collection": collection, "document_type": document_type},
            files={"file": (filename, text.encode(), "text/plain")},
        )
        if response.status_code != 201:
            raise SystemExit(
                f"Failed to seed {filename}: HTTP {response.status_code} {response.text}"
            )

        payload = response.json()
        if payload.get("status") != "indexed":
            raise SystemExit(f"Seed document {filename} was not indexed: {payload}")


def run_case(client: TestClient, index: int, case: dict[str, Any]) -> CaseResult:
    name = str(case.get("name") or f"case-{index}")
    question = require_string(case, "question", name)
    expected_sources = require_string_list(case, "expected_sources", name)
    expected_answer_contains = require_string_list(case, "expected_answer_contains", name)

    request_body: dict[str, Any] = {
        "query": question,
        "top_k": int(case.get("top_k", 5)),
    }
    if case.get("collection") is not None:
        request_body["collection"] = require_string(case, "collection", name)
    if case.get("similarity_score_threshold") is not None:
        request_body["similarity_score_threshold"] = float(case["similarity_score_threshold"])

    response = client.post("/api/v1/rag/answer", json=request_body)
    if response.status_code != 200:
        return CaseResult(
            name=name,
            passed=False,
            source_passed=False,
            answer_passed=False,
            no_context_passed=False if not expected_sources else None,
            expected_sources=expected_sources,
            actual_sources=[],
            missing_phrases=expected_answer_contains,
            answer=f"HTTP {response.status_code}: {response.text}",
        )

    payload = response.json()
    citations = payload.get("citations", [])
    actual_sources = [
        citation.get("source", "") for citation in citations if isinstance(citation, dict)
    ]
    answer = str(payload.get("answer", ""))

    source_passed = all(source in actual_sources for source in expected_sources)
    if not expected_sources:
        source_passed = actual_sources == []

    missing_phrases = [phrase for phrase in expected_answer_contains if phrase not in answer]
    answer_passed = not missing_phrases

    no_context_passed = None
    if not expected_sources:
        no_context_passed = (
            payload.get("retrieved_chunks_count") == 0
            and citations == []
            and answer == INSUFFICIENT_CONTEXT_ANSWER
        )

    passed = source_passed and answer_passed and (no_context_passed is not False)
    return CaseResult(
        name=name,
        passed=passed,
        source_passed=source_passed,
        answer_passed=answer_passed,
        no_context_passed=no_context_passed,
        expected_sources=expected_sources,
        actual_sources=actual_sources,
        missing_phrases=missing_phrases,
        answer=answer,
    )


def require_string(payload: dict[str, Any], key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"{label} must include a non-empty string field '{key}'.")
    return value


def require_string_list(payload: dict[str, Any], key: str, label: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"{label} must include a string list field '{key}'.")
    return value


def pass_fail(value: bool) -> str:
    return "pass" if value else "fail"


if __name__ == "__main__":
    raise SystemExit(main())
