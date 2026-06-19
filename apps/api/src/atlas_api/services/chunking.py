from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from atlas_api.schemas.chunks import ChunkCreate


@dataclass(frozen=True)
class TextSegment:
    text: str
    section: str | None


class ChunkingService:
    _TEXT_SUFFIXES = {".txt", ".text"}
    _MARKDOWN_SUFFIXES = {".md", ".markdown"}
    _PDF_SUFFIXES = {".pdf"}

    def __init__(self, max_characters: int = 1_000) -> None:
        self._max_characters = max_characters

    def chunk_document(self, filename: str, content: bytes) -> list[ChunkCreate]:
        suffix = PurePath(filename).suffix.lower()
        supported_suffixes = self._TEXT_SUFFIXES | self._MARKDOWN_SUFFIXES | self._PDF_SUFFIXES
        if suffix not in supported_suffixes:
            return []

        text = self._extract_pdf_text(content) if suffix in self._PDF_SUFFIXES else (
            content.decode("utf-8", errors="ignore")
        )
        text = text.replace("\x00", "").strip()
        if not text:
            return []

        segments = self._markdown_segments(text) if suffix in self._MARKDOWN_SUFFIXES else [
            TextSegment(text=text, section=None)
        ]
        chunks: list[ChunkCreate] = []

        for segment in segments:
            for chunk_text in self._paragraph_chunks(segment.text):
                chunks.append(
                    ChunkCreate(
                        chunk_index=len(chunks),
                        text=chunk_text,
                        section=segment.section,
                        character_count=len(chunk_text),
                    )
                )

        return chunks

    def _markdown_segments(self, text: str) -> list[TextSegment]:
        segments: list[TextSegment] = []
        current_section: str | None = None
        current_lines: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip()
                if heading:
                    self._append_segment(segments, current_lines, current_section)
                    current_section = heading
                    current_lines = [heading]
                    continue

            current_lines.append(line)

        self._append_segment(segments, current_lines, current_section)
        return segments or [TextSegment(text=text, section=None)]

    def _append_segment(
        self,
        segments: list[TextSegment],
        lines: list[str],
        section: str | None,
    ) -> None:
        text = "\n".join(lines).strip()
        if text:
            segments.append(TextSegment(text=text, section=section))

    def _paragraph_chunks(self, text: str) -> list[str]:
        paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
        if not paragraphs:
            return self._fixed_chunks(text)

        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            if len(paragraph) > self._max_characters:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._fixed_chunks(paragraph))
                continue

            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if len(candidate) <= self._max_characters:
                current = candidate
            else:
                chunks.append(current)
                current = paragraph

        if current:
            chunks.append(current)

        return chunks

    def _fixed_chunks(self, text: str) -> list[str]:
        return [
            text[start : start + self._max_characters].strip()
            for start in range(0, len(text), self._max_characters)
            if text[start : start + self._max_characters].strip()
        ]

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))
        except (PdfReadError, ValueError):
            return ""

        page_text = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                page_text.append(extracted)

        return "\n\n".join(page_text)
