"""
Tests for utils.misc.

Covers: get_defined_function_names, get_function_calls, get_function_ranges.
"""

from utils.misc import (
    get_defined_function_names,
    get_function_calls,
    get_function_ranges,
)


class TestUtils:
    """Test suite for utils.misc."""

    def test_get_function_calls_with_classes(self):
        """Test get_function_calls with class methods."""
        code = """
def foo():
    return 1

class MyClass:
    def method_one(self):
        self.helper()
        return 3
    
    def helper(self):
        return 4

obj = MyClass()
obj.method_one()
foo()
"""
        result = get_function_calls(code, only_defined_in_code=True)

        # Check that calls are found and sorted by line number
        assert 7 in result  # self.helper() call
        assert 14 in result  # obj.method_one() call
        assert 15 in result  # foo() call

        # Check that method calls include class name
        assert "MyClass.helper" in result[7]
        assert "MyClass.method_one" in result[14]

        # Check that regular function calls don't include class name
        assert "foo" in result[15]

    def test_get_defined_function_names(self):
        """Test get_defined_function_names with classes."""
        code = """
def foo():
    pass

class MyClass:
    def method_one(self):
        pass
    
    def helper(self):
        pass
"""
        result = get_defined_function_names(code)

        assert "foo" in result
        assert "MyClass.method_one" in result
        assert "MyClass.helper" in result
        assert "method_one" not in result  # Should have class prefix
        assert "helper" not in result  # Should have class prefix

    def test_get_function_ranges_with_multiline_string(self):
        """get_function_ranges includes full body when triple-quoted string exists."""
        code = '''def main():
    message = """안녕하세요.
이것은 여러 줄로 이루어진
문자열입니다."""
    print(message)

if __name__ == "__main__":
    main()
'''
        result = get_function_ranges(code)
        assert len(result) == 1
        main = result[0]
        assert main["name"] == "main"
        assert main["type"] == "def"
        assert main["startLine"] == 0
        # Function body ends at print(message); trailing blank line included
        assert main["endLine"] == 5
