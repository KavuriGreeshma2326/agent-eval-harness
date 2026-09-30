# Agent Evaluation Harness

A small harness for evaluating LLM agents on command-line tasks. Each task runs in its own
Docker container with no network access. An agent works inside the container one shell
command at a time, then hidden tests decide whether it succeeded. Every trial is saved as a
JSON record (steps, tokens, stated confidence, outcome) so results can be compared across
models and repeated runs.

## Task format

Each task is a folder under `tasks/`:

```
tasks/<task-id>/
├── task.json              # id, difficulty, max_steps, command and test timeouts
├── instruction.md         # what the agent is asked to do
├── environment/
│   └── Dockerfile         # the container the agent works in (plus any data files)
├── solution/
│   └── solve.sh           # reference solution, used only by the oracle agent
└── tests/
    ├── test.sh            # entry point; exit code 0 means the task passed
    └── test_output.py     # the actual checks
```

## Quickstart

Requirements: Python 3.10+ and Docker (running).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # then put your API key in .env
```

The LLM agent uses any OpenAI-compatible endpoint, configured in `.env`
(`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and optionally `LLM_MIN_INTERVAL_SEC` to
space out requests for rate-limited providers).

```bash
python run.py validate --all                                  # check every task is well-formed
python run.py --all --agent llm --trials 5                    # run the LLM agent
python run.py --all --agent llm --trials 5 --model <model>    # override the model from .env
python report.py                                              # summarize all saved runs
```

## How a trial works

1. Build the task's Docker image and start a container with no network, 1 GB RAM and 1 CPU.
2. Run the agent. The LLM agent replies with one JSON action per turn: either a shell
   command, or `done` with a confidence between 0 and 1. Each command has a timeout, and
   long output is truncated.
3. After the agent stops, copy `tests/` into the container and run `tests/test.sh`.
4. Save the trial record to `runs/` and remove the container.

Each trial ends with one outcome: `passed`, `failed`, or `infra_error`.

## Tasks

There are 11 tasks: 3 easy, 5 medium and 3 hard, covering log and data processing,
config debugging, fixing broken code, multi-file reasoning, date logic, a database
migration and flaky-test debugging. Each is designed so that a careless agent can be
confident and still wrong. See [docs/tasks.md](docs/tasks.md) for what each task tests
and how its tests catch common wrong answers.

## Design choices

- **No network in the sandbox.** The agent has to solve the task with what is in the
  container, and cannot download answers or reach external services.
- **Tests are copied in only after the agent finishes.** The agent never sees the checks,
  so it cannot pass by reading or editing them.
- **Oracle/NOP validation.** A task is only valid if the reference solution passes and an
  agent that does nothing fails. This catches broken tests and tasks that pass by default.
- **Infra errors are excluded from pass rates.** If the LLM API or Docker fails, the trial
  is recorded as `infra_error` and does not count as an agent failure. The agent's own
  shell commands never raise exceptions (failures come back as exit codes), so any
  exception during a trial is an infrastructure problem.
- **Confidence is recorded at the moment the agent declares done.** Trials that stop for
  other reasons (step limit, repeated invalid replies) have no confidence value.

## Status

Implemented:
- Task format, Docker sandbox, oracle and nop agents
- 11 validated tasks across three difficulty levels
- LLM agent loop with JSON actions, stated confidence and token tracking
- Multi-task, multi-trial runs with a model override
- Separation of infra errors from agent failures
- `validate` command
- Results report (pass rate, steps, tokens, average confidence, infra errors)

Planned:
- pass@k
- Calibration analysis (Brier score, ECE)
- Failure taxonomy (automatic and manual labels)
- Multi-model results

## Acknowledgements

The task format is inspired by [Terminal-Bench](https://github.com/laude-institute/terminal-bench).
Tasks other than log-5xx-summary were drafted with AI assistance (Claude) and validated
with oracle and nop runs.
