import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    total_chunks: int
    note_id: str
    metadata: Dict[str, Any]


class RecursiveChunker:
    def __init__(
        self,
        max_chunk_size: int = 800,
        overlap_ratio: float = 0.5,
        min_chunk_size: int = 50,
        chunk_by_divider: bool = True,
        chunk_by_heading: bool = True,
        chunk_by_paragraph: bool = True,
        chunk_by_sentence: bool = True
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap_ratio = overlap_ratio
        self.min_chunk_size = min_chunk_size

        self.chunk_by_divider = chunk_by_divider
        self.chunk_by_heading = chunk_by_heading
        self.chunk_by_paragraph = chunk_by_paragraph
        self.chunk_by_sentence = chunk_by_sentence

    def split_by_divider(self, text: str) -> List[str]:
        parts = text.split('\n---\n')
        return [p.strip() for p in parts if p.strip()]

    def split_by_headings(self, text: str) -> List[str]:
        heading_pattern = r'^(#{1,6}\s+.+)$'
        lines = text.split('\n')

        sections = []
        current_section = []

        for line in lines:
            if re.match(heading_pattern, line, re.MULTILINE):
                if current_section:
                    sections.append('\n'.join(current_section))
                    current_section = []
            current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section))

        return [s.strip() for s in sections if s.strip()]

    def split_by_paragraphs(self, text: str) -> List[str]:
        paragraphs = re.split(r'\n\n+', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def split_by_sentences(self, text: str) -> List[str]:
        sentence_pattern = r'(?<=[。！？.!?])\s*'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def add_overlap(self, chunks: List[str]) -> List[Tuple[str, str]]:
        if len(chunks) <= 1:
            return [(c, "") for c in chunks]

        overlap_size = int(self.max_chunk_size * self.overlap_ratio)
        result = []

        for i, chunk in enumerate(chunks):
            if len(chunk) <= self.max_chunk_size:
                if i < len(chunks) - 1:
                    next_overlap = chunks[i + 1][:overlap_size]
                    combined = chunk + "\n" + next_overlap
                else:
                    combined = chunk
                result.append((combined, chunk[:50] if len(chunk) > 50 else chunk))
            else:
                result.append((chunk[:self.max_chunk_size], chunk[:50]))

        return result

    def recursive_chunk(self, text: str, level: int = 1) -> List[str]:
        if not text or not text.strip():
            return []

        if len(text) <= self.max_chunk_size:
            return [text]

        chunks = []

        if level == 1 and self.chunk_by_divider:
            chunks = self.split_by_divider(text)
        elif level == 2 and self.chunk_by_heading:
            chunks = self.split_by_headings(text)
        elif level == 3 and self.chunk_by_paragraph:
            chunks = self.split_by_paragraphs(text)
        elif level == 4 and self.chunk_by_sentence:
            chunks = self.split_by_sentences(text)

        if not chunks:
            if level < 4:
                return self.recursive_chunk(text, level + 1)
            else:
                return [text[:self.max_chunk_size]]

        if len(chunks) == 1 and len(chunks[0]) > self.max_chunk_size:
            if level < 4:
                return self.recursive_chunk(text, level + 1)
            else:
                return [text[:self.max_chunk_size]]

        if all(len(c) <= self.max_chunk_size for c in chunks):
            return chunks

        if level < 4:
            merged = []
            for chunk in chunks:
                if len(chunk) <= self.max_chunk_size:
                    merged.append(chunk)
                else:
                    sub_chunks = self.recursive_chunk(chunk, level + 1)
                    merged.extend(sub_chunks)
            return merged

        return [text[:self.max_chunk_size]]

    def chunk(self, note_id: str, title: str, content: str) -> List[TextChunk]:
        if not content or not content.strip():
            return [TextChunk(
                content=f"{title}",
                chunk_index=0,
                total_chunks=1,
                note_id=note_id,
                metadata={"type": "title_only"}
            )]

        combined = f"{title}\n{content}"
        raw_chunks = self.recursive_chunk(combined, level=1)

        chunks_with_overlap = self.add_overlap(raw_chunks)

        result_chunks = []
        for i, (chunk_content, _) in enumerate(chunks_with_overlap):
            if len(chunk_content) >= self.min_chunk_size:
                result_chunks.append(TextChunk(
                    content=chunk_content,
                    chunk_index=i,
                    total_chunks=len(chunks_with_overlap),
                    note_id=note_id,
                    metadata={"level": 1}
                ))

        total = len(result_chunks)
        for c in result_chunks:
            c.total_chunks = total

        return result_chunks
