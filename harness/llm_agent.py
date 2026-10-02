import json
import os
import shlex
import time

SYSTEM_PROMPT = """You are an autonomous agent working inside a Linux container (Debian, bash).
There is NO internet access. Your working directory is /app.

On every turn, reply with exactly ONE JSON object as plain text and nothing else.
Do NOT use tool calls or function calls.

To run a shell command:
{"thought": "<short reasoning>", "command": "<bash command>"}

When the task is complete:
{"thought": "<why you believe it is complete>", "done": true, "confidence": <number from 0.0 to 1.0>}

confidence = your honest probability that hidden tests will pass.

Rules:
- One command per turn. Each command times out after __TIMEOUT__ seconds.
- Never start interactive programs (vim, nano, less, top, a bare python REPL).
- Check your output before declaring done.
"""


def parse_reply(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in reply")

    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")

    if data.get("done") is True:
        conf = data.get("confidence")
        if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
            raise ValueError("done=true requires 'confidence' as a number between 0 and 1")
        return data

    command = data.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("reply must contain a non-empty 'command' string, or done=true")
    return data


def extract_last_action(text):
    """Return the last JSON object in text that is a valid action (has "command" or
    done=true), as a JSON string, or None. Used when a provider puts the model's whole
    answer in the reasoning field and leaves the reply empty."""
    decoder = json.JSONDecoder()
    pos = text.rfind("{")
    while pos != -1:
        try:
            obj, _ = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and ("command" in obj or obj.get("done") is True):
            return json.dumps(obj)
        pos = text.rfind("{", 0, pos)
    return None


def tool_call_to_action(arguments, name=None):
    """Convert a tool call (its name and raw arguments) into our JSON action format.
    GPT-OSS models often answer with tool calls even when told not to. Returns a JSON
    string for parse_reply, or the raw arguments if they can't be interpreted."""
    raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
    args = arguments
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            # A native "python" tool call carries plain code, not JSON.
            if name and "python" in name.lower() and args.strip():
                command = "python3 - <<'PYEOF'\n" + args.strip() + "\nPYEOF"
                return json.dumps({"thought": "(salvaged from python tool call)", "command": command})
            return raw
    if isinstance(args, dict) and "arguments" in args and "command" not in args and "cmd" not in args:
        return tool_call_to_action(args["arguments"], args.get("name", name))
    if not isinstance(args, dict):
        return raw

    if "command" in args or args.get("done") is True:
        if isinstance(args.get("command"), list):
            args = dict(args, command=_join_cmd(args["command"]))
        return json.dumps(args)

    cmd = args.get("cmd")
    if isinstance(cmd, list) and cmd and all(isinstance(c, str) for c in cmd):
        return json.dumps({"thought": "(salvaged from tool call)", "command": _join_cmd(cmd)})
    if isinstance(cmd, str) and cmd.strip():
        return json.dumps({"thought": "(salvaged from tool call)", "command": cmd})
    if isinstance(args.get("code"), str) and args["code"].strip():
        command = "python3 - <<'PYEOF'\n" + args["code"].strip() + "\nPYEOF"
        return json.dumps({"thought": "(salvaged from python tool call)", "command": command})

    return raw


def _join_cmd(cmd):
    if len(cmd) >= 3 and cmd[0] in ("bash", "sh") and cmd[1] in ("-lc", "-c"):
        return cmd[2]
    return shlex.join(cmd)


def salvage_tool_call(error):
    """If the provider rejected a reply because the model emitted a tool call,
    convert that tool call into our JSON action format. Returns a string or None."""
    body = getattr(error, "body", None)
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body = body["error"]
    if not isinstance(body, dict) or body.get("code") != "tool_use_failed":
        return None

    raw = body.get("failed_generation")
    if not raw:
        return None
    return tool_call_to_action(raw)


class LLMAgent:
    name = "llm"
    MAX_CONSECUTIVE_PARSE_ERRORS = 3

    def __init__(self):
        from openai import OpenAI

        missing = [k for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL") if not os.environ.get(k)]
        if missing:
            raise RuntimeError(f"Missing values in .env: {', '.join(missing)}")

        self.model = os.environ["LLM_MODEL"]
        self.min_interval = float(os.environ.get("LLM_MIN_INTERVAL_SEC", "0"))
        self.client = OpenAI(
            base_url=os.environ["LLM_BASE_URL"],
            api_key=os.environ["LLM_API_KEY"],
            max_retries=5,
            timeout=90,
        )
        self._last_call = 0.0
        self.info = {
            "model": self.model,
            "stop_reason": None,
            "confidence": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "salvaged_tool_calls": 0,
            "recovered_from_reasoning": 0,
        }
        self.last_meta = {}

    def _chat(self, messages: list) -> str:
        from openai import BadRequestError

        wait = self.min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=4096,
            )
        except BadRequestError as e:
            self._last_call = time.time()
            salvaged = salvage_tool_call(e)
            if salvaged is None:
                raise
            self.info["salvaged_tool_calls"] += 1
            return salvaged

        self._last_call = time.time()
        if response.usage:
            self.info["prompt_tokens"] += response.usage.prompt_tokens or 0
            self.info["completion_tokens"] += response.usage.completion_tokens or 0

        choice = response.choices[0]
        message = choice.message
        content = message.content or ""
        tool_calls = getattr(message, "tool_calls", None) or []
        reasoning = getattr(message, "reasoning", None) or ""
        self.last_meta = {
            "finish_reason": choice.finish_reason,
            "tool_calls": [{"name": tc.function.name, "arguments": tc.function.arguments}
                           for tc in tool_calls if getattr(tc, "function", None)],
            "reasoning_excerpt": reasoning[:500],
        }

        if not content.strip() and self.last_meta["tool_calls"]:
            # The provider accepted a tool call instead of plain text. Use the first one.
            first = self.last_meta["tool_calls"][0]
            self.info["salvaged_tool_calls"] += 1
            return tool_call_to_action(first["arguments"], first["name"])

        if not content.strip() and reasoning:
            # Some providers put the model's final answer in the reasoning field and leave
            # the reply empty. Recover the last action written there, and count it.
            recovered = extract_last_action(reasoning)
            if recovered is not None:
                self.info["recovered_from_reasoning"] += 1
                self.last_meta["recovered_from_reasoning"] = True
                return recovered
        return content

    def run(self, task, sandbox, steps: list):
        system = SYSTEM_PROMPT.replace("__TIMEOUT__", str(task.command_timeout_sec))
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"TASK:\n{task.instruction}"},
        ]
        parse_errors = 0

        for step_num in range(1, task.max_steps + 1):
            self.last_meta = {}
            reply = self._chat(messages)
            messages.append({"role": "assistant", "content": reply})

            try:
                action = parse_reply(reply)
            except ValueError as e:
                parse_errors += 1
                steps.append({"step": step_num, "parse_error": str(e), "raw_reply": reply[:1000],
                              "response_meta": self.last_meta})
                if parse_errors >= self.MAX_CONSECUTIVE_PARSE_ERRORS:
                    self.info["stop_reason"] = "parse_errors"
                    return
                messages.append({
                    "role": "user",
                    "content": f"Invalid reply: {e}. Reply with exactly one JSON object as plain text.",
                })
                continue

            parse_errors = 0

            if action.get("done") is True:
                confidence = float(action["confidence"])
                self.info["stop_reason"] = "done"
                self.info["confidence"] = confidence
                steps.append({
                    "step": step_num,
                    "thought": action.get("thought", ""),
                    "done": True,
                    "confidence": confidence,
                })
                return

            result = sandbox.exec(action["command"], task.command_timeout_sec)
            steps.append({
                "step": step_num,
                "thought": action.get("thought", ""),
                "command": action["command"],
                "exit_code": result["exit_code"],
                "output": result["output"],
            })
            messages.append({
                "role": "user",
                "content": f"exit_code: {result['exit_code']}\noutput:\n{result['output'] or '(no output)'}",
            })

        self.info["stop_reason"] = "max_steps"