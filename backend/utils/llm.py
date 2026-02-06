from openai import OpenAI

from settings import settings
import utils

client = OpenAI(api_key=settings.OPENAI_API_KEY)


CODE_REQUIREMENTS = """
# Prompt

## Mini-Function Definition
A Mini-Function has a very simple structure:
- 20 lines or less
- No try-catch: error handling is delegated to subordinate functions
- Complex logic or detailed implementation should be separated into separate functions
- No async functions: Mini-Functions must be synchronous
- Avoid complex behavior:
    - No nested function calls: assign function results to variables first, e.g., use `headers = get_headers()` then `requests.post(url, headers=headers)` instead of `requests.post(url, get_headers())`
    - No list, dictionary, or set comprehensions, or generator expressions: use explicit for loops instead
    - No ternary operators: use explicit if-else statements instead
    - No function definitions inside Mini-Function body: never creates closures
    - No chained method calls: assign intermediate results to variables, e.g., use `result = obj.method1()` then `final = result.method2()` instead of `obj.method1().method2()`
    - No multiple assignments from function calls: assign each result separately, e.g., use `a = func1()` then `b = func2()` instead of `a, b = func1(), func2()`

## Subordinate-Function Definition
- Name starts with `_` (underscore prefix), e.g., `_fetch_data(url)`, `_add_header()`
- Any function needed: write as needed without restrictions

# Program structure
- The program should have a main function that is a Mini-Function.
- A Mini-Function can call either Mini-Functions or Subordinate-Functions, but Subordinate-Functions can only call Subordinate-Functions
- Mini-Functions can be nested in multiple layers as needed
- Maximize Mini-Functions: make functions Mini-Functions as much as possible.
- Only the final dirty implementation details are handled by subordinate functions.
"""


def generate_code_with_llm(
    request: str,
    model: str = "gpt-4.1-mini",
    temperature: float = 1.0,  # Value btw 0 and 2. TODO: tune this
    max_tokens: int = 3000,
) -> str:
    """
    Generate code based on a natural language request using LLM.

    Args:
        request: Natural language description of the code to generate
        model: The LLM model to use
        temperature: Controls randomness in the output
        max_tokens: Maximum number of tokens in the response

    Returns:
        Generated code based on the request
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{CODE_REQUIREMENTS}\n\n"
                    f"Generate code based on the following request:\n\n"
                    f"{request}\n\n"
                    "Provide only the code without any explanations or comments. "
                    "Make sure the code is complete and ready to run."
                ),
            }
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    code = response.choices[0].message.content.strip()

    # Remove code block markers if present
    if code.startswith("```python"):
        code = code[9:]  # Remove ```python
    elif code.startswith("```"):
        code = code[3:]  # Remove ```

    if code.endswith("```"):
        code = code[:-3]  # Remove trailing ```

    code = code.strip()

    return code


DIFF_FORMAT = """
The V4A diff format expresses code changes with clear context.

- Each change is shown with surrounding context: by default, include 3 lines above and 3 lines below the modified code.
- Do not duplicate context: if two changes occur within 3 lines of each other, the overlapping context lines should only appear once.
- Removed lines start with '-', added lines start with '+'.
- A single diff can contain multiple hunks, each beginning with one or more @@ annotations.
- No line numbers are used; context and optional @@ scope annotations are sufficient to uniquely identify each hunk.
- If context alone is insufficient to uniquely identify the location, use the @@ operator to specify the containing class or function.

For example, here is a single hunk:

@@ class BaseClass
     def __init__(self, x, y):
         self.x = x
         self.y = y
-        self.result = None
+        self.result = 0
         self.ready = True
         self.version = 1

If a code block is repeated so many times in a class or function such that even a single @@ statement and 3 lines of context cannot uniquely identify the snippet, you can use multiple @@ statements. For instance:

@@ class BaseClass
@@ def method1(self):
         for i in range(10):
-            total += i
+            total += i * 2
         return total
 
     def method2(self):

- A single diff can contain multiple hunks.

@@ class BaseClass
     def __init__(self, x, y):
         self.x = x
         self.y = y
-        self.result = None
+        self.result = 0
         self.ready = True
         self.version = 1

@@ class BaseClass
@@ def method1(self):
         for i in range(10):
-            total += i
+            total += i * 2
         return total
 
     def method2(self):
"""


def _get_diff(
    code: str,
    request: str,
    selected_lines: str | None = None,
    execution_history: list[dict] | None = None,
    # NOTE gpt-5 does not support temperature other than 1.0. To use a lower
    # temperature, use gpt-4.1.
    model: str = "gpt-4.1",
    temperature: float = 0.5,
    # max_tokens: int = 3000,
) -> str:
    """
    Edit existing code based on a natural language request using LLM.

    Args:
        code: The existing code to edit
        request: Natural language description of the changes to make
        selected_lines: The actual selected lines of code (if any) to focus the edit on
        model: The LLM model to use
        temperature: Controls randomness in the output
        max_tokens: Maximum number of tokens in the response

    Returns:
        Unified diff format showing the changes made to the code
    """
    # Define single template with built-in string substitution
    template = (
        "Given the following code:\n\n"
        "{code}\n\n"
        "{selected_lines_content}"
        "{execution_history_content}"
        "Please make the following changes: {request}\n\n"
        "{focus_instruction}"
        "Return the result in V4A diff. {diff_format}"
    )

    # Build additional content based on whether we have selected lines
    selected_lines_content = ""
    focus_instruction = ""
    execution_history_content = ""

    if selected_lines:
        selected_lines_content = (
            "The user has selected these specific lines to focus on:\n\n"
            "```\n{selected_lines}\n```\n\n"
        ).format(selected_lines=selected_lines)
        focus_instruction = (
            "IMPORTANT: Focus your changes primarily on the selected lines "
            "above, but you may make related changes elsewhere in the code "
            "if necessary to implement the request properly.\n\n"
        )

    if execution_history:
        execution_history_content = (
            "The user has attached this execution trace:\n\n" "{execution_history}\n\n"
        ).format(execution_history=execution_history)

    # Build the prompt using built-in string formatting
    prompt_content = template.format(
        code=code,
        selected_lines_content=selected_lines_content,
        execution_history_content=execution_history_content,
        request=request,
        focus_instruction=focus_instruction,
        diff_format=DIFF_FORMAT,
    )

    options = {}
    if not model.startswith("gpt-5"):
        options["temperature"] = (
            temperature  # gpt-5 does not support temperature option
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt_content,
            }
        ],
        **options,
        # max_tokens=max_tokens,
    )

    diff = response.choices[0].message.content.strip()
    return diff


def edit_code_with_llm(
    code: str,
    request: str,
    selected_lines: str | None = None,
    execution_history: list[dict] | None = None,
) -> str:
    from apply_patch import process_patch

    if settings.DEBUG:
        print(f"request: {request}")
        if selected_lines:
            print(f"selected_lines: {selected_lines}")
        if execution_history:
            print(f"execution_history: {execution_history}")

    diff = _get_diff(code, request, selected_lines, execution_history)

    if settings.DEBUG:
        print(f"diff: {diff}")

    patch_text = f"""*** Begin Patch
{diff}
*** End Patch
"""
    updated_code = process_patch(code, patch_text)
    return updated_code


# TODO: Get additional relevant code context (function definitions) from the entire code
# Should be sufficient to list after stepping in?


def explain_step(
    code: str,
    delta: dict,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.5,
) -> str:
    executed_code = delta["executed_code"]
    context = delta["context"]
    captured_calls = delta["captured_calls"]

    prompt = f"""# Debugger Step Explanation Prompt
You are a helpful assistant that explains debugger execution steps to a programming novice. Your goal is to make complex code behavior understandable using simple, clear language.

## Core Rule
You MUST ONLY describe the effect of the SINGLE executed line.
- Only explain the impact of the line.
- Do not mention lines that have not executed yet.
- Do not speculate about future results or errors.

## Guidelines
- Use simple words and avoid technical jargon
- Keep the explanation to one short sentence whenever possible
- Focus on what actually happened, not just what the code says
- Explain the impact or result of the step, not just the syntax
- Avoid unnecessary subjects when the action is clear 
  - Example: "Stored the number 10 into x" instead of "The program stored..."
- When a function call happens:
  - Mention the action in plain words
  - Include key input values if they are short
- When an error occurs (very important):
  - Emphasize the error first
  - Summarize the message in plain words (include exact text if short)
  - Mention that the error was stored into the variable
  - If obvious, explain the root cause in plain words
  - Never stop at just describing the function call if an error was returned

## Examples

### Example 1:

Executed code:
x = 10

Context:
  1  -> x = 10
  2     y = 20
  3  
  4  
  5     def add_numbers(a, b):
  6         result = a + b
  7         print(f"Adding {{a}} and {{b}}")
  8         return result

Captured calls:
[]

---

Explanation:
Stored the number 10 into the variable x.


### Example 2:

Executed code:
sum_result = add_numbers(x, y)

Context:
 14         return result
 15  
 16  
 17     # Main execution
 18     print("Starting calculation...")
 19  -> sum_result = add_numbers(x, y)
 20     print(f"Sum: {{sum_result}}")
 21     product_result = multiply_numbers(x, y)
 22     print(f"Product: {{product_result}}")
 23     final_result = add_numbers(sum_result, product_result)
 24     print(f"Final result: {{final_result}}")

Captured calls:
[{{'type': 'call', 'function': 'add_numbers()', 'parameters': {{'a': '10', 'b': '20'}}, 'return_value': '30'}}]

---

Explanation:
Added 10 and 20 together using the function and saved the answer, 30, as sum_result.


### Example 3:

Executed code:
ret = place_order(“KRW-XRP”, “buy”, volume=1.0, price=4240.0, ord_type=“price”)

Context:
50  -> ret = place_order(“KRW-XRP”, “buy”, volume=1.0, price=4240.0, ord_type=“price”)

Captured calls:
[{{'type': 'call', 'function': 'place_order()',
'parameters': {{'market': 'KRW-XRP', 'side': 'buy',
'volume': '1.0', 'price': '4240.0', 'ord_type': 'price'}},
'return_value': {{'error': {{'message': '잘못된 파라미터', 'name': 'invalid_parameter'}}}}}}]

Output:
Tried to place an order, but the function returned an error saying “잘못된 파라미터” (invalid parameter), and that error was saved into ret.


### Actual:

Executed code:
{executed_code}

Context:
{context}

Captured calls:
{captured_calls}

Explanation:
"""

    if settings.DEBUG:
        print("\n--prompt--")
        # TODO make it more pretty
        print(f"{executed_code}\n{captured_calls}\n")

    options = {}
    if not model.startswith("gpt-5"):
        options["temperature"] = (
            temperature  # gpt-5 does not support temperature option
        )
    response = client.chat.completions.create(
        model=model,
        **options,
        messages=[{"role": "user", "content": prompt}],
    )
    response = response.choices[0].message.content.strip()

    if settings.DEBUG:
        print("\n--response--")
        print(response)
        print("\n")

    return response


if __name__ == "__main__":
    from apply_patch import process_patch

    with open(
        settings.PROJECT_CONTAINERS_DIR / "1" / "1" / "data" / "main.py", "r"
    ) as f:
        code = f.read()

    diff = _get_diff(code, "Remove multiply_numbers")

    # Define the patch text in proper V4A format
    patch_text = (
        "*** Begin Patch",
        f"\n{diff}\n",
        "*** End Patch",
    )
    updated_code = process_patch(code, patch_text)

    from debug import DebugSession

    debugger = DebugSession(code)
    for i in range(5):
        msg = debugger.step_over()
    # Get delta from execution_history
    if debugger.execution_history:
        delta = debugger.execution_history[-1].get("delta")
        ret = explain_step(code, delta)
    print(ret)

    ###
    # Test execution history integration using actual debugging session
    print("\n" + "=" * 50)
    print("Testing execution history integration...")

    # Get execution history from the debugging session
    execution_history = debugger.execution_history[-4:]
    print("\n--execution_history--")
    print(execution_history)
    print("\n")

    print("✓ Found execution history from debugging session")
    print(f"Execution history steps: {len(execution_history)}")

    test_request = "Add error handling to the functions"

    try:
        diff_with_history = _get_diff(
            code=code, request=test_request, execution_history=execution_history
        )
        print("✓ Success: Generated diff with execution history")
        print(f"Diff length: {len(diff_with_history)} characters")
        print(diff_with_history)
    except Exception as e:
        print(f"✗ Error with execution history: {e}")
