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

    try:
        generation = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    args = generation.get("arguments", generation) if isinstance(generation, dict) else None
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return raw
    if not isinstance(args, dict):
        return raw

    if "command" in args or args.get("done") is True:
        return json.dumps(args)

    cmd = args.get("cmd")
    if isinstance(cmd, list) and cmd and all(isinstance(c, str) for c in cmd):
        if len(cmd) >= 3 and cmd[0] in ("bash", "sh") and cmd[1] in ("-lc", "-c"):
            command = cmd[2]
        else:
            command = shlex.join(cmd)
        return json.dumps({"thought": "(salvaged from tool call)", "command": command})
    if isinstance(cmd, str) and cmd.strip():
        return json.dumps({"thought": "(salvaged from tool call)", "command": cmd})

    return raw


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
        }

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
        return response.choices[0].message.content or ""

    def run(self, task, sandbox, steps: list):
        system = SYSTEM_PROMPT.replace("__TIMEOUT__", str(task.command_timeout_sec))
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"TASK:\n{task.instruction}"},
        ]
        parse_errors = 0

        for step_num in range(1, task.max_steps + 1):
            reply = self._chat(messages)
            messages.append({"role": "assistant", "content": reply})

            try:
                action = parse_reply(reply)
            except ValueError as e:
                parse_errors += 1
                steps.append({"step": step_num, "parse_error": str(e), "raw_reply": reply[:1000]})
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