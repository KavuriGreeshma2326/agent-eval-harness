import subprocess
import uuid

MAX_OUTPUT_CHARS = 4000


class SandboxError(RuntimeError):
    """Docker build/start/copy failed. This is an infrastructure problem, not an agent failure."""


class Sandbox:
    def __init__(self, task):
        self.task = task
        self.image = f"aeh-{task.id}:latest"
        self.container = None

    def build(self):
        result = subprocess.run(
            ["docker", "build", "-t", self.image, str(self.task.path / "environment")],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise SandboxError(f"Docker build failed:\n{result.stderr[-2000:]}")

    def start(self):
        name = f"aeh-{self.task.id}-{uuid.uuid4().hex[:8]}"
        result = subprocess.run(
            [
                "docker", "run", "-d", "--rm",
                "--name", name,
                "--network", "none",
                "--memory", "1g",
                "--cpus", "1",
                self.image, "sleep", "infinity",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise SandboxError(f"Container start failed:\n{result.stderr}")
        self.container = name

    def exec(self, command: str, timeout_sec: int) -> dict:
        try:
            result = subprocess.run(
                ["docker", "exec", self.container,
                 "timeout", str(timeout_sec), "bash", "-lc", command],
                capture_output=True, text=True, timeout=timeout_sec + 10,
            )
        except subprocess.TimeoutExpired:
            return {"exit_code": 124, "output": "[harness] command timed out"}

        output = result.stdout + result.stderr
        if len(output) > MAX_OUTPUT_CHARS:
            half = MAX_OUTPUT_CHARS // 2
            output = output[:half] + "\n...[output truncated]...\n" + output[-half:]
        return {"exit_code": result.returncode, "output": output}

    def copy_in(self, local_dir, container_dir: str):
        result = subprocess.run(
            ["docker", "cp", f"{local_dir}/.", f"{self.container}:{container_dir}"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise SandboxError(f"docker cp failed:\n{result.stderr}")

    def stop(self):
        if self.container:
            subprocess.run(["docker", "rm", "-f", self.container], capture_output=True)
            self.container = None