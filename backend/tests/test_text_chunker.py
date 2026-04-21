import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.text_chunker import RecursiveChunker, TextChunk


class TestRecursiveChunker:
    def setup_method(self):
        self.chunker = RecursiveChunker(
            max_chunk_size=800,
            overlap_ratio=0.5,
            min_chunk_size=50
        )

    def test_split_by_divider(self):
        text = "第一部分\n---\n第二部分\n---\n第三部分"
        chunks = self.chunker.split_by_divider(text)
        assert len(chunks) == 3
        assert chunks[0] == "第一部分"
        assert chunks[1] == "第二部分"
        assert chunks[2] == "第三部分"

    def test_split_by_divider_empty_parts(self):
        text = "第一部分\n---\n\n---\n第二部分"
        chunks = self.chunker.split_by_divider(text)
        assert len(chunks) == 2

    def test_split_by_headings(self):
        text = "# 标题1\n内容1\n## 标题2\n内容2"
        chunks = self.chunker.split_by_headings(text)
        assert len(chunks) == 2
        assert "# 标题1" in chunks[0]
        assert "## 标题2" in chunks[1]

    def test_split_by_headings_multiple_levels(self):
        text = "# 主标题\n内容1\n## 子标题1\n内容2\n### 孙标题\n内容3\n## 子标题2\n内容4"
        chunks = self.chunker.split_by_headings(text)
        assert len(chunks) >= 2
        assert "# 主标题" in chunks[0]

    def test_split_by_paragraphs(self):
        text = "段落1\n\n段落2\n\n段落3"
        chunks = self.chunker.split_by_paragraphs(text)
        assert len(chunks) == 3
        assert chunks[0] == "段落1"
        assert chunks[1] == "段落2"
        assert chunks[2] == "段落3"

    def test_split_by_sentences(self):
        text = "这是第一句。这是第二句！这是第三句？这是第四句。"
        chunks = self.chunker.split_by_sentences(text)
        assert len(chunks) == 4
        assert chunks[0] == "这是第一句。"
        assert chunks[1] == "这是第二句！"
        assert chunks[2] == "这是第三句？"
        assert chunks[3] == "这是第四句。"

    def test_recursive_chunk_short_text(self):
        text = "短文本内容，不超过800字符。" * 10
        chunks = self.chunker.recursive_chunk(text)
        assert len(chunks) == 1

    def test_recursive_chunk_long_text(self):
        long_text = "内容。" * 500
        chunks = self.chunker.recursive_chunk(long_text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 800

    def test_add_overlap_50_percent(self):
        chunks = ["块1内容" * 100, "块2内容" * 100, "块3内容" * 100]
        result = self.chunker.add_overlap(chunks)
        assert len(result) == 3
        overlap_size = int(800 * 0.5)
        assert len(result[0][0]) > len(chunks[0])

    def test_add_overlap_single_chunk(self):
        chunks = ["单个块"]
        result = self.chunker.add_overlap(chunks)
        assert len(result) == 1
        assert result[0][0] == "单个块"

    def test_empty_text(self):
        chunks = self.chunker.recursive_chunk("")
        assert chunks == []

    def test_none_text(self):
        chunks = self.chunker.recursive_chunk(None)
        assert chunks == []

    def test_whitespace_only_text(self):
        chunks = self.chunker.recursive_chunk("   \n\n   \t  ")
        assert chunks == []

    def test_pure_heading_text(self):
        text = "# 标题1\n## 子标题1\n### 孙标题"
        chunks = self.chunker.recursive_chunk(text)
        assert len(chunks) >= 1

    def test_chunk_method_with_content(self):
        title = "测试笔记"
        content = "# 第一章\n内容...\n---\n# 第二章\n内容..." * 20
        result_chunks = self.chunker.chunk("note_1", title, content)
        assert len(result_chunks) > 0
        for chunk in result_chunks:
            assert isinstance(chunk, TextChunk)
            assert chunk.note_id == "note_1"
            assert len(chunk.content) >= 50

    def test_chunk_method_title_only(self):
        result_chunks = self.chunker.chunk("note_2", "只有标题", "")
        assert len(result_chunks) == 1
        assert result_chunks[0].metadata["type"] == "title_only"

    def test_chunk_method_total_count(self):
        title = "测试笔记"
        content = "内容。" * 200
        result_chunks = self.chunker.chunk("note_3", title, content)
        if result_chunks:
            total = result_chunks[0].total_chunks
            for chunk in result_chunks:
                assert chunk.total_chunks == total

    def test_min_chunk_size_filter(self):
        small_chunker = RecursiveChunker(
            max_chunk_size=800,
            overlap_ratio=0.5,
            min_chunk_size=100
        )
        text = "短。" * 5
        chunks = small_chunker.recursive_chunk(text)
        result = small_chunker.chunk("note_4", "测试", text)
        for chunk in result:
            assert len(chunk.content) >= 100


class TestEdgeCases:
    def setup_method(self):
        self.chunker = RecursiveChunker(max_chunk_size=800, overlap_ratio=0.5)

    def test_very_long_single_paragraph(self):
        long_para = "这是一个超长的段落。" * 300
        chunks = self.chunker.recursive_chunk(long_para)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 800

    def test_mixed_content_types(self):
        mixed = """# 标题
一些内容。

---

## 另一个标题
更多内容。

这是普通文本。还有特殊字符：@#$%^&*()
"""
        chunks = self.chunker.recursive_chunk(mixed)
        assert len(chunks) >= 1

    def test_unicode_content(self):
        unicode_text = "中文内容。日本語。한국어. العربية. 🎉🚀"
        chunks = self.chunker.recursive_chunk(unicode_text)
        assert len(chunks) >= 1

    def test_special_markdown_chars(self):
        md_text = """# 标题 **加粗** *斜体*
- 列表项1
- 列表项2

```python
代码块
```

> 引用文本
"""
        chunks = self.chunker.recursive_chunk(md_text)
        assert len(chunks) >= 1

    def test_only_newlines(self):
        chunks = self.chunker.recursive_chunk("\n\n\n\n")
        assert chunks == []

    def test_exact_max_chunk_size(self):
        exact_text = "A" * 800
        chunks = self.chunker.recursive_chunk(exact_text)
        assert len(chunks) == 1
        assert len(chunks[0]) == 800

    def test_one_char_over_max(self):
        over_text = "A" * 801
        chunks = self.chunker.recursive_chunk(over_text)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk) <= 800


class TestConfiguration:
    def test_custom_max_chunk_size(self):
        custom = RecursiveChunker(max_chunk_size=400, overlap_ratio=0.5)
        text = "内容。" * 200
        chunks = custom.recursive_chunk(text)
        for chunk in chunks:
            assert len(chunk) <= 400

    def test_custom_overlap_ratio(self):
        custom = RecursiveChunker(max_chunk_size=800, overlap_ratio=0.25)
        chunks = ["A" * 600, "B" * 600, "C" * 600]
        result = custom.add_overlap(chunks)
        expected_overlap = int(800 * 0.25)
        assert len(result[0][0]) == 600 + 1 + expected_overlap

    def test_disable_heading_split(self):
        no_heading = RecursiveChunker(
            max_chunk_size=800,
            chunk_by_heading=False
        )
        text = "# 标题\n" + "内容。\n" * 200
        chunks = no_heading.recursive_chunk(text)
        assert len(chunks) >= 1


class TestPerformance:
    def test_chunking_performance_3000_chars(self):
        import time
        chunker = RecursiveChunker(max_chunk_size=800, overlap_ratio=0.5)
        long_content = "这是一段测试内容。" * 500

        start = time.time()
        for _ in range(100):
            chunker.recursive_chunk(long_content)
        elapsed = (time.time() - start) / 100 * 1000

        assert elapsed < 10, f"分块耗时 {elapsed:.2f}ms，超过10ms限制"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
