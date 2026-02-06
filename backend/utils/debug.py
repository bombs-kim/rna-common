import base64
import json
import re

from steps_project_engine.manage import get_container_data_dir, create_debug_process
from utils.misc import get_function_calls

from utils.debug_tree_source import BUILD_VAR_TREE_SOURCE as _BUILD_VAR_TREE_SOURCE

PDB_PROMPT = "(Pdb) "
CALL_PATTERN = "--Call--"
RETURN_PATTERN = "--Return--"
PROGRAM_FINISHED_PATTERN = "The program finished and will be restarted"


FRAME_WITH_CODE_PATTERN = re.compile(
    r"^(?:\s{2}|>\s)([^(\s]+)\((\d+)\)([^\n]+)\n->([^\n]+)\n"
)
FRAME_STRING_PATTERN = re.compile(r"^(?:\s{2}|>\s)<([^>]+)>\((\d+)\)(.+)")


def _get_function_name_and_retval(function_name: str):
    if "->" in function_name:
        idx = function_name.index("->")
        _function_name = function_name[:idx]
        retval = function_name[idx + 2 :]
        return {
            "function": _function_name,
            "retval": retval,
        }
    else:
        return {"function": function_name}


def parse_pdb_output(output_text):
    """
    Parse pdb output and return program_output and frames
    """
    lines = output_text.split("\n")

    # Find where the frame information starts
    frame_start_idx = None
    for i, line in enumerate(lines):
        # Look for frame output but not list output (numbered lines)
        # Frame output examples:
        #   - Next/step commands: "> /path/file.py(10)<module>()"
        #   - Where command: "  /path/file.py(10)<module>()"
        # List output examples (should be excluded):
        #   - "  1  ->	x = 10"
        #   - "  2  	y = 20"
        if (
            re.match(r"^\s*>", line) or re.match(r"^\s+[^(]+\(\d+\)", line)
        ) and not re.match(r"^\s*\d+\s+", line):
            frame_start_idx = i
            break

    # Extract program output (everything before frames)
    program_output = (
        "\n".join(lines[:frame_start_idx])
        if frame_start_idx is not None
        else output_text
    )

    # Extract frames (everything from frame_start_idx onwards)
    frames = []
    if frame_start_idx is not None:
        frame_lines = lines[frame_start_idx:]

        i = 0
        while i < len(frame_lines):
            line = frame_lines[i]

            # Try to match frame with code (2-line pattern)
            match1 = FRAME_WITH_CODE_PATTERN.match(
                "\n".join(frame_lines[i : i + 2]) + "\n"
            )
            if match1:
                frame = {
                    "file": match1.group(1),
                    "line": int(match1.group(2)),
                    "code": match1.group(4),
                    "is_current": line.startswith(">"),
                }
                frame.update(_get_function_name_and_retval(match1.group(3)))
                frames.append(frame)
                i += 2
                continue

            # Try to match string frame (single line pattern)
            match2 = FRAME_STRING_PATTERN.match(line)
            if match2:
                frame = {
                    "file": match2.group(1),
                    "line": int(match2.group(2)),
                    "is_current": line.startswith(">"),
                }
                frame.update(_get_function_name_and_retval(match2.group(3)))
                frames.append(frame)
                i += 1
                continue

            # Skip unmatched lines
            i += 1

    return program_output, frames


class DebugSession:
    def __init__(self, container_name):
        self.container_name = container_name
        self.filename = "main.py"  # TODO make this configurable
        user_id, project_id = self.container_name.split("-")[1:]
        filepath = get_container_data_dir(user_id, project_id) / self.filename
        with open(filepath, "r") as f:
            self.code = f.read()

        self.user_defined_function_calls = get_function_calls(self.code)

        self.current_frame = None
        self.execution_history = []
        self.process = create_debug_process(user_id, project_id)

        _ = self._read_user_and_pdb_output()
        self._inject_build_var_tree()

    def _inject_build_var_tree(self):
        """Inject build_var_tree into debuggee global scope so we can call it via pdb_p."""
        b64 = base64.b64encode(_BUILD_VAR_TREE_SOURCE.encode()).decode()
        cmd = '!exec(__import__("base64").b64decode({}).decode())\n'.format(
            json.dumps(b64)
        )
        self.process.stdin.write(cmd)
        self.process.stdin.flush()
        _ = self._read_user_and_pdb_output()

    def _finish(self):
        # send ctrl+d to pdb
        self.process.stdin.write("q\n")
        self.process.stdin.flush()
        self.process.wait()
        self.process = None
        self.code = None

    @property
    def is_finished(self):
        return self.process is None

    def _read_up_to(self, pattern: str):
        """Read stdout up to the pattern. The pattern is included in the output."""
        output = ""
        while True:
            char = self.process.stdout.read(1)

            # TODO verify if this is a desirable behavior
            if not char:
                break

            output += char

            # Check if we have the pattern in our buffer
            if output.endswith(pattern):
                break

        return output

    def _read_user_and_pdb_output(self):
        raw_output = self._read_up_to(PDB_PROMPT).replace(PDB_PROMPT, "")
        program_output, frames = parse_pdb_output(raw_output)

        pdb_output = ""

        for pattern in (CALL_PATTERN, RETURN_PATTERN, PROGRAM_FINISHED_PATTERN):
            if pattern in raw_output:
                pdb_output = pattern
                idx = raw_output.index(pattern)
                # TODO ask LLM if these assumptions are correct
                # NOTE this assumes that the pattern always follows the program output
                # NOTE this assumes that only one pattern is found
                program_output = raw_output[:idx]
                break

        return program_output, pdb_output, frames

    def ensure_process_is_running(self):
        if not self.process or self.process.poll() is not None:
            raise Exception("Program finished")

    def pdb_next(self):
        """Step over the current line (next command in pdb)"""
        self.ensure_process_is_running()

        # Send 'n' command to pdb for next line
        self.process.stdin.write("n\n")
        self.process.stdin.flush()

        program_output, pdb_output, _ = self._read_user_and_pdb_output()
        return program_output, pdb_output

    def pdb_step(self):
        """Step into the current line (step command in pdb)"""
        self.ensure_process_is_running()
        self.process.stdin.write("s\n")
        self.process.stdin.flush()

        program_output, pdb_output, _ = self._read_user_and_pdb_output()
        return program_output, pdb_output

    def pdb_return(self):
        """Step out of the current function (return command in pdb)"""
        self.ensure_process_is_running()
        self.process.stdin.write("r\n")
        self.process.stdin.flush()
        program_output, pdb_output, frames = self._read_user_and_pdb_output()

        for frame in frames:
            if frame.get("is_current", False):
                current_frame = frame
                break

        assert "retval" in current_frame
        retval = current_frame["retval"]

        return program_output, pdb_output, retval

    def pdb_where(self):
        """
        in pdb, where prints a stack trace, with the most recent frame at the
        bottom. An arrow (>) indicates the current frame, which determines the
        context of most commands.
        """
        self.ensure_process_is_running()

        # Send 'w' command to pdb for stack trace
        self.process.stdin.write("w\n")
        self.process.stdin.flush()

        program_output, output, frames = self._read_user_and_pdb_output()
        assert program_output == ""
        return frames

    def pdb_up(self):
        self.ensure_process_is_running()
        self.process.stdin.write("up\n")
        self.process.stdin.flush()
        program_output, _, _ = self._read_user_and_pdb_output()
        return program_output

    def pdb_down(self):
        raise NotImplementedError

    def pdb_list(self):
        """List source code around the current line (list command in pdb)"""
        self.ensure_process_is_running()
        self.process.stdin.write("l .\n")
        self.process.stdin.flush()
        program_output, _, _ = self._read_user_and_pdb_output()
        return program_output

    def pdb_longlist(self):
        """List more source code around the current line (longlist command in pdb)"""
        self.ensure_process_is_running()
        self.process.stdin.write("ll\n")
        self.process.stdin.flush()
        program_output, _, _ = self._read_user_and_pdb_output()
        return program_output

    def pdb_p(self, expr):
        self.ensure_process_is_running()
        self.process.stdin.write(f"p {expr}\n")
        self.process.stdin.flush()
        program_output, _, _ = self._read_user_and_pdb_output()
        return program_output

    def pdb_break(self, location):
        """Set a breakpoint at the specified location (function name or line number)"""
        self.ensure_process_is_running()
        self.process.stdin.write(f"b {location}\n")
        self.process.stdin.flush()
        program_output, _, _ = self._read_user_and_pdb_output()
        return program_output

    def pdb_continue(self):
        """Continue execution until the next breakpoint"""
        self.ensure_process_is_running()
        self.process.stdin.write("c\n")
        self.process.stdin.flush()
        program_output, pdb_output, frames = self._read_user_and_pdb_output()
        return program_output, pdb_output, frames

    ###########################################################################

    def _step_over_and_capture_calls(self):
        """
        Step over the current line while capturing all function parameters and return values.
        Handles cases where one line has multiple function calls (e.g., a = fn2(fn1())).
        Returns a dictionary of captured function calls with their parameters and return values.
        """
        captured_calls = []

        program_output_list = []

        while True:
            # Try to step into the current line
            initial_frames = self.pdb_where()
            for idx, frm in enumerate(initial_frames):
                if frm.get("is_current", False):
                    break
            initial_frames = initial_frames[: idx + 1]

            program_output, pdb_output = self.pdb_step()

            if self.is_exception_raised():
                # Capture exception information and store it into captured calls
                exception_info = self._capture_exception_info()
                captured_calls.append({"type": "exception", **exception_info})
                program_output_list.append(program_output)
                break

            program_output_list.append(program_output)

            # Check if we actually stepped into a function
            new_frames = self.pdb_where()
            if len(new_frames) > len(initial_frames):
                # We stepped into a function, capture parameters first
                # Note that we we get local vars as soon as we step into a function,
                # then all the local variables are only function parameters,
                # not variables defined inside the function body.
                function_name = new_frames[-1]["function"]
                vars = self.get_local_vars()
                params = {name: vars[name]["repr_tree"]["value"] for name in vars}

                # Check if we're in a generator function
                is_in_generator = self._is_in_generator_function()

                # TODO do not ignore generator, but handle yield values

                if is_in_generator:
                    # For generators, we can't use pdb_return() as they don't have traditional returns
                    # Instead, we'll step out using pdb_up() and set return_value to None
                    self.pdb_up()
                    program_output, pdb_output = self.pdb_next()
                    program_output_list.append(program_output)
                    retval_repr = None
                    break
                else:
                    # For regular functions, step out and capture return value
                    program_output, pdb_output, retval_repr = self.pdb_return()
                    program_output_list.append(program_output)

                    captured_calls.append(
                        {
                            "type": "call",
                            "function": function_name,
                            "parameters": params,
                            "return_value": retval_repr,
                        }
                    )
            else:
                # Step in didn't work, we're at a non-function line
                # 's' already executed the line and moved forward
                break

        program_output = "\n".join(program_output_list)
        # TODO See if pdb_output is correctly set
        return program_output, pdb_output, captured_calls

    def _step_over_and_capture_delta(self):
        """
        Step over the current line while capturing function calls and line context.
        Captures the source code listing before and after stepping over.
        Returns user output, pdb output, captured calls, and line context.
        """

        # Capture initial state (source code listing before stepping)
        context = self.pdb_list()

        executed_code = self.get_current_frame().get("code", "")

        # Run the step over and capture calls
        program_output, pdb_output, captured_calls = self._step_over_and_capture_calls()

        if PROGRAM_FINISHED_PATTERN in pdb_output:
            raise RuntimeError(
                "Unexpected program finished state in _step_over_and_capture_delta. "
                "This should not be reachable."
            )

        # Combine all context information
        delta = {
            "executed_code": executed_code,
            "context": context,
            "captured_calls": captured_calls,
        }

        return program_output, pdb_output, delta

    def is_exception_raised(self):
        program_output = self.pdb_p("__exception__")
        if program_output.startswith("*** NameError"):
            return False
        else:
            return True

    def _capture_exception_info(self):
        """
        Capture detailed information about the current exception.
        Returns a dictionary with exception type, message, and traceback information.
        """
        # Get the exception object
        exception_output = self.pdb_p("__exception__")

        # Get traceback information
        traceback_frames = self.pdb_where()

        return {
            "exception_repr": exception_output.rstrip(),
            "traceback": traceback_frames,
        }

    def get_local_vars(self, max_depth=4, max_children=64):
        """Return current frame locals as a dict: var_name -> {"id": int, "repr_tree": node}."""
        expr = "__import__('json').dumps(build_var_tree(locals(), %d, %d))" % (
            max_depth,
            max_children,
        )
        raw = self.pdb_p(expr).strip()
        # p prints the repr of the result, so we get a quoted/escaped string; eval to get the string
        try:
            json_str = eval(raw)
        except Exception:
            return {}
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}

    def _is_in_generator_function(self):
        """
        Check if the current function is a generator function by examining the code object.
        Returns True if the current frame is in a generator function, False otherwise.
        """
        try:
            # Check if the code object has the CO_GENERATOR flag
            # CO_GENERATOR = 0x20 (32 in decimal)
            to_eval = self.pdb_p("$_frame.f_code.co_flags & 0x20")
            flags_result = to_eval.strip()

            # If the result is not "0", then it's a generator
            return flags_result != "0"
        except Exception:
            # If we can't determine, assume it's not a generator
            return False

    def get_current_frame(self):
        frames = self.pdb_where()
        local_vars = self.get_local_vars()

        # Find the current frame (marked with is_current=True)
        for frame in frames:
            if frame.get("is_current", False):
                ret_frame = {
                    "filename": frame["file"],
                    "function": frame["function"],
                    "line_number": frame["line"],
                    "local_vars": local_vars,
                }
                if "code" in frame:
                    ret_frame["code"] = frame["code"]
                if "retval" in frame:
                    ret_frame["retval"] = frame["retval"]
                return ret_frame
        raise Exception("No current frame found")

    def get_cumulative_program_output(self):
        """Get cumulative program output from all steps in execution_history."""
        if not self.execution_history:
            return ""

        # Concatenate all program_output from execution_history
        program_outputs = []
        for entry in self.execution_history:
            if "program_output" in entry and entry["program_output"]:
                program_outputs.append(entry["program_output"])

        return "\n".join(program_outputs)

    ###########################################################################

    def _store_step_info(
        self, step_type, program_output, pdb_output, current_frame, **kwargs
    ):
        """Store step information for debugging and analysis purposes."""
        entry = {
            "step_type": step_type,
            "program_output": program_output,
            "pdb_output": pdb_output,
            "current_frame": current_frame,
        }
        entry.update(kwargs)

        self.execution_history.append(entry)

    def step_over(self):
        state = self.get_state()
        is_already_returning = state["is_returning"]
        is_already_in_main = state["is_in_main"]

        # This can only happen when the previous operation was
        # a step_out from the last function call of the last line of the main function
        if is_already_returning and is_already_in_main:
            self._finish()
            return

        program_output, pdb_output, delta = self._step_over_and_capture_delta()
        self._store_step_info(
            "step_over",
            program_output=program_output,
            pdb_output=pdb_output,
            current_frame=self.get_current_frame(),
            delta=delta,
        )

        was_returning = is_already_returning
        state = self.get_state()
        is_returning = state["is_returning"]
        is_in_main = state["is_in_main"]

        if is_returning and is_in_main:
            # Continue first to make sure the program runs to the end
            self.pdb_continue()
            # Call _finish() to quit pdb, since pdb will restart the program
            # automatically if we don't
            self._finish()
            return

        if not was_returning and is_returning:
            program_output, pdb_output, delta = self._step_over_and_capture_delta()
            # Store step information
            self._store_step_info(
                "step_over",
                program_output=program_output,
                pdb_output=pdb_output,
                current_frame=self.get_current_frame(),
                delta=delta,
            )

    def explain_step(self):
        """
        Generate explanation for the last step in execution_history.
        Returns the explanation string.
        """
        from .llm import explain_step

        if not self.execution_history:
            raise Exception("No execution history available for explanation")

        # Get the last step's delta from execution_history
        last_entry = self.execution_history[-1]
        if "delta" not in last_entry:
            raise Exception("Last step does not have delta information")

        delta = last_entry["delta"]
        explanation = explain_step(self.code, delta)

        # Update the last entry with the explanation
        last_entry["explanation"] = explanation

        return explanation

    def can_step_into(self):
        """
        Check if we can step into a user-defined function call on the current line.
        Returns True if the current line contains a call to a user-defined function, False otherwise.
        """
        current_frame = self.get_current_frame()
        if not current_frame or "line_number" not in current_frame:
            return False

        line_number = current_frame["line_number"]
        return line_number in self.user_defined_function_calls

    def can_step_out(self):
        """
        Check if we're inside the main function. If not, we can step out.
        Returns True if we're not in the main function (can step out), False otherwise.
        """
        current_frame = self.get_current_frame()
        function_name = current_frame["function"]
        return not function_name.startswith("main(")

    def get_state(self):
        frame = self.get_current_frame()
        state = {
            "filename": frame["filename"],
            "line_number": frame["line_number"],
            "local_vars": frame["local_vars"],
            "can_step_into": self.can_step_into(),
            "can_step_out": self.can_step_out(),
            "is_returning": "retval" in frame,
            "is_in_main": frame.get("function", "").startswith("main("),
        }
        if "code" in frame:
            state["code"] = frame["code"]

        return state

    def step_into(self):
        # Get initial frame stack length
        initial_frames = self.pdb_where()
        initial_frame_count = len(initial_frames)

        # Step into
        program_output, pdb_output = self.pdb_step()

        # Check if frame changed (stepped into a function)
        new_frames = self.pdb_where()
        new_frame_count = len(new_frames)

        # If frame changed and stepped in worked, do self.pdb_next() once.
        # It will prepare the arguments for the next step.
        if new_frame_count > initial_frame_count:
            program_output, pdb_output = self.pdb_next()

        if PROGRAM_FINISHED_PATTERN in pdb_output:
            raise RuntimeError(
                "Unexpected program finished state in step_into. "
                "This should not be reachable."
            )

        # Store step information
        self._store_step_info(
            "step_into",
            program_output=program_output,
            pdb_output=pdb_output,
            current_frame=self.get_current_frame(),
        )

    def step_out(self):
        program_output, pdb_output, _ = self.pdb_return()

        # After return, use _step_over_and_capture_delta to move forward and capture delta
        program_output, pdb_output, delta = self._step_over_and_capture_delta()

        # Store step information with delta
        self._store_step_info(
            "step_out",
            program_output=program_output,
            pdb_output=pdb_output,
            current_frame=self.get_current_frame(),
            delta=delta,
        )


if __name__ == "__main__":
    sess = DebugSession("project-1-1")
    sess.pdb_break("main")
    sess.pdb_continue()
    # sess.step_over()
    # sess.get_current_frame()
