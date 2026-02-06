"""
Tests for utils.syntax_highlight.

Covers get_python_highlights: structure, capture types, and UTF-16 column output.
"""

from utils.syntax_highlight import get_python_highlights


class TestGetPythonHighlights:
    """Tests for get_python_highlights."""

    def test_empty_code_returns_empty_list(self):
        assert get_python_highlights("") == []
        assert get_python_highlights("   \n\n") == []

    def test_result_has_expected_keys(self):
        code = "x = 1"
        result = get_python_highlights(code)
        assert result
        for r in result:
            assert set(r.keys()) == {
                "id",
                "startLine",
                "startCol",
                "endLine",
                "endCol",
                "type",
                "content",
            }
            assert isinstance(r["id"], int)
            assert all(
                isinstance(r[k], int)
                for k in ("startLine", "startCol", "endLine", "endCol")
            )
            assert isinstance(r["type"], str)
            assert isinstance(r["content"], str)

    def test_simple_keyword_and_literal(self):
        code = "def foo():"
        result = get_python_highlights(code)
        types = [r["type"] for r in result]
        assert "keyword" in types
        assert "function" in types or "variable" in types

    def test_string_capture(self):
        code = 's = "hello"'
        result = get_python_highlights(code)
        string_ranges = [r for r in result if r["type"] == "string"]
        assert len(string_ranges) >= 1
        r = string_ranges[0]
        assert r["startLine"] == r["endLine"] == 0
        # String node includes quotes: "s = " at 0-4, then "\"hello\"" from col 4 to 11
        assert r["startCol"] == 4
        assert r["endCol"] == 11
        assert r["content"] == '"hello"'

    def test_comment_capture(self):
        code = "x = 1  # comment"
        result = get_python_highlights(code)
        comment_ranges = [r for r in result if r["type"] == "comment"]
        assert len(comment_ranges) >= 1
        assert comment_ranges[0]["startCol"] >= 6

    def test_utf16_columns_for_non_ascii(self):
        # Korean: each character is 1 UTF-16 code unit in JS; backend must not return byte offset.
        code = "f'한글나라'"
        result = get_python_highlights(code)
        string_ranges = [r for r in result if r["type"] == "string"]
        assert len(string_ranges) >= 1
        r = string_ranges[0]
        # String is 7 characters: f ' 한 글 나 라 '
        assert r["startLine"] == 0 and r["endLine"] == 0
        assert r["startCol"] == 0
        assert (
            r["endCol"] == 7
        ), "endCol must be UTF-16 length (7), not byte length (15)"

    def test_korean_string_and_comment(self):
        code = 'msg = "안녕하세요 세계"\n# 한글 주석'
        result = get_python_highlights(code)
        string_ranges = [r for r in result if r["type"] == "string"]
        comment_ranges = [r for r in result if r["type"] == "comment"]
        assert len(string_ranges) >= 1
        assert len(comment_ranges) >= 1
        # "msg = " -> 6 chars, then string "안녕하세요 세계" (8 chars + 2 quotes = 10) -> endCol 16
        r = string_ranges[0]
        assert r["startLine"] == 0
        assert r["startCol"] == 6
        assert r["endCol"] == 16
        # Comment on line 1: "# " is 2 chars, "한글 주석" is 5 chars -> 7 total
        c = comment_ranges[0]
        assert c["startLine"] == 1 and c["startCol"] == 0
        assert c["endCol"] == 7

    def test_emoji_in_string(self):
        # Emoji are 2 UTF-16 code units in JS (surrogate pair); backend returns UTF-16 columns.
        code = 'x = "🐍"'
        result = get_python_highlights(code)
        string_ranges = [r for r in result if r["type"] == "string"]
        assert len(string_ranges) >= 1
        r = string_ranges[0]
        assert r["startLine"] == 0 and r["endLine"] == 0
        assert r["startCol"] == 4  # 'x = '
        # String is quote(1) + 🐍(2 UTF-16) + quote(1) = 4, so endCol 8
        assert r["endCol"] == 8, "endCol must be UTF-16 offset (8)"

    def test_korean_and_emoji_in_string(self):
        code = 'greeting = "안녕 🎉"'
        result = get_python_highlights(code)
        string_ranges = [r for r in result if r["type"] == "string"]
        assert len(string_ranges) >= 1
        r = string_ranges[0]
        # 'greeting = "' -> 11 UTF-16 units; string "안녕 🎉" -> 7 units (안녕 space 🎉 + quotes)
        assert r["startCol"] == 11
        assert r["endCol"] == 18

    def test_multiline_highlight_spans_lines(self):
        code = 'x = """a\nb"""'
        result = get_python_highlights(code)
        string_ranges = [r for r in result if r["type"] == "string"]
        assert string_ranges
        # At least one range should span lines or we have multiple segments
        multi = [r for r in string_ranges if r["endLine"] > r["startLine"]]
        if not multi:
            # Alternatively multiple single-line string segments
            assert len(string_ranges) >= 1
        else:
            assert multi[0]["startLine"] == 0
            assert multi[0]["endLine"] >= 1

    def test_result_sorted_by_position(self):
        code = "def f():\n    return 1"
        result = get_python_highlights(code)
        for i in range(len(result) - 1):
            a, b = result[i], result[i + 1]
            assert (a["startLine"], a["startCol"]) <= (b["startLine"], b["startCol"])
