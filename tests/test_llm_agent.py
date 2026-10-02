import json
import unittest
from types import SimpleNamespace as NS

from harness.llm_agent import (LLMAgent, extract_last_action, parse_reply,
                               salvage_tool_call, tool_call_to_action)


def response(content=None, tool_calls=None, finish_reason="stop", reasoning=None):
    calls = [NS(function=NS(name=n, arguments=a)) for n, a in (tool_calls or [])]
    message = NS(content=content, tool_calls=calls or None, reasoning=reasoning)
    return NS(choices=[NS(message=message, finish_reason=finish_reason)],
              usage=NS(prompt_tokens=10, completion_tokens=5))


def agent_with(replies):
    """An LLMAgent whose API client returns the given fake responses in order."""
    agent = LLMAgent.__new__(LLMAgent)
    agent.model, agent.min_interval, agent._last_call = "fake", 0, 0.0
    agent.info = {"model": "fake", "stop_reason": None, "confidence": None,
                  "prompt_tokens": 0, "completion_tokens": 0, "salvaged_tool_calls": 0,
                  "recovered_from_reasoning": 0}
    agent.last_meta = {}
    queue = list(replies)
    agent.client = NS(chat=NS(completions=NS(create=lambda **kw: queue.pop(0))))
    return agent


class ToolCallConversionTests(unittest.TestCase):
    def action(self, arguments, name=None):
        return parse_reply(tool_call_to_action(arguments, name))

    def test_cmd_list_with_bash(self):
        self.assertEqual(self.action('{"cmd": ["bash", "-lc", "ls /app"]}')["command"], "ls /app")

    def test_cmd_list_plain(self):
        self.assertEqual(self.action('{"cmd": ["cat", "/app/a b.txt"]}')["command"], "cat '/app/a b.txt'")

    def test_cmd_string(self):
        self.assertEqual(self.action('{"cmd": "ls -la"}')["command"], "ls -la")

    def test_command_field(self):
        self.assertEqual(self.action('{"command": "pwd"}')["command"], "pwd")

    def test_done_field(self):
        self.assertEqual(self.action('{"done": true, "confidence": 0.8}')["confidence"], 0.8)

    def test_nested_arguments(self):
        raw = json.dumps({"name": "container.exec", "arguments": {"cmd": ["bash", "-lc", "id"]}})
        self.assertEqual(self.action(raw)["command"], "id")

    def test_python_tool_with_plain_code(self):
        command = self.action("print(1 + 1)", name="python")["command"]
        self.assertIn("print(1 + 1)", command)
        self.assertTrue(command.startswith("python3 - <<'PYEOF'"))

    def test_uninterpretable_returns_raw(self):
        self.assertEqual(tool_call_to_action('{"query": "weather"}'), '{"query": "weather"}')


class ExtractFromReasoningTests(unittest.TestCase):
    def test_text_then_json(self):
        text = 'We need to run tests to see failures.{"thought":"List files", "command":"ls -R"}'
        self.assertEqual(parse_reply(extract_last_action(text))["command"], "ls -R")

    def test_takes_last_action(self):
        text = 'Maybe {"command": "ls"} ... actually {"thought": "t", "command": "pwd"}'
        self.assertEqual(parse_reply(extract_last_action(text))["command"], "pwd")

    def test_braces_inside_command(self):
        text = 'Use awk. {"thought": "x", "command": "awk \'{print $1}\' /app/f.txt"}'
        self.assertEqual(parse_reply(extract_last_action(text))["command"], "awk '{print $1}' /app/f.txt")

    def test_done_action(self):
        text = 'All good. {"thought": "done", "done": true, "confidence": 0.9}'
        self.assertEqual(parse_reply(extract_last_action(text))["confidence"], 0.9)

    def test_no_action(self):
        self.assertIsNone(extract_last_action("I should look at the files first."))
        self.assertIsNone(extract_last_action('some json {"a": 1} but no action'))


class SalvageErrorTests(unittest.TestCase):
    def test_rejected_tool_call(self):
        gen = json.dumps({"name": "container.exec", "arguments": {"cmd": ["bash", "-lc", "ls"]}})
        error = NS(body={"error": {"code": "tool_use_failed", "failed_generation": gen}})
        self.assertEqual(parse_reply(salvage_tool_call(error))["command"], "ls")

    def test_other_errors_not_salvaged(self):
        self.assertIsNone(salvage_tool_call(NS(body={"error": {"code": "rate_limit"}})))


class ChatTests(unittest.TestCase):
    def test_plain_json_reply(self):
        agent = agent_with([response('{"thought": "x", "command": "ls"}')])
        self.assertEqual(parse_reply(agent._chat([]))["command"], "ls")
        self.assertEqual(agent.info["salvaged_tool_calls"], 0)

    def test_accepted_tool_call_with_empty_content(self):
        agent = agent_with([response("", tool_calls=[("container.exec", '{"cmd": ["bash", "-lc", "ls"]}')])])
        self.assertEqual(parse_reply(agent._chat([]))["command"], "ls")
        self.assertEqual(agent.info["salvaged_tool_calls"], 1)
        self.assertEqual(agent.info["completion_tokens"], 5)  # usage is still counted

    def test_empty_reply_records_metadata(self):
        agent = agent_with([response("", finish_reason="length", reasoning="thinking...")])
        self.assertEqual(agent._chat([]), "")
        self.assertEqual(agent.last_meta["finish_reason"], "length")
        self.assertEqual(agent.last_meta["reasoning_excerpt"], "thinking...")


class ReasoningRecoveryTests(unittest.TestCase):
    def test_empty_reply_with_action_in_reasoning(self):
        reasoning = 'We need to run tests.{"thought":"Run tests", "command":"cd /app/project && python3 -m unittest -q"}'
        agent = agent_with([response("", reasoning=reasoning)])
        action = parse_reply(agent._chat([]))
        self.assertEqual(action["command"], "cd /app/project && python3 -m unittest -q")
        self.assertEqual(agent.info["recovered_from_reasoning"], 1)
        self.assertTrue(agent.last_meta["recovered_from_reasoning"])

    def test_normal_reply_ignores_reasoning(self):
        agent = agent_with([response('{"command": "ls"}', reasoning='{"command": "rm -rf /"}')])
        self.assertEqual(parse_reply(agent._chat([]))["command"], "ls")
        self.assertEqual(agent.info["recovered_from_reasoning"], 0)


class RunTests(unittest.TestCase):
    def test_tool_call_then_done(self):
        agent = agent_with([
            response(None, tool_calls=[("container.exec", '{"cmd": ["bash", "-lc", "echo hi"]}')]),
            response('{"thought": "ok", "done": true, "confidence": 0.7}'),
        ])
        sandbox = NS(exec=lambda cmd, timeout: {"exit_code": 0, "output": "hi"})
        task = NS(command_timeout_sec=30, instruction="do it", max_steps=5)
        steps = []
        agent.run(task, sandbox, steps)
        self.assertEqual(steps[0]["command"], "echo hi")
        self.assertEqual(agent.info["stop_reason"], "done")
        self.assertEqual(agent.info["confidence"], 0.7)

    def test_parse_error_step_includes_metadata(self):
        empty = response("", finish_reason="stop")
        agent = agent_with([empty, empty, empty])
        steps = []
        agent.run(NS(command_timeout_sec=30, instruction="x", max_steps=5), None, steps)
        self.assertEqual(agent.info["stop_reason"], "parse_errors")
        self.assertEqual(steps[0]["response_meta"]["finish_reason"], "stop")


if __name__ == "__main__":
    unittest.main()
