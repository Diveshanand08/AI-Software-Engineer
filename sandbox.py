"""
sandbox.py
Executes arbitrary Python code inside an isolated Docker container.

Safety measures:
- No network access (network_disabled=True) - generated code can't exfiltrate data
- Memory limit (default 256MB) - prevents runaway memory usage
- CPU limit (default 0.5 cores) - prevents runaway CPU usage
- Hard timeout (default 10s) - kills the container if code hangs (infinite loops etc.)
- Read-only bind mount - the code file is copied in, not the whole filesystem
- Container is removed after every run (no leftover state between runs)

Usage:
    from sandbox import run_code_in_sandbox
    result = run_code_in_sandbox("print('hello')")
    print(result.stdout, result.stderr, result.exit_code, result.timed_out)

CLI usage:
    python sandbox.py --file path/to/script.py
    python sandbox.py --code "print(1+1)"
"""

import argparse
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

DEFAULT_IMAGE = "python:3.11-slim"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_MEMORY_LIMIT = "256m"
DEFAULT_CPU_QUOTA = 50000  # 0.5 CPU core (quota is in units of 100000 = 1 core)


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    error: str | None = None


def _get_client() -> docker.DockerClient:
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        raise RuntimeError(
            "Could not connect to Docker. Is Docker Desktop installed and running? "
            f"Original error: {e}"
        )


def run_code_in_sandbox(
    code: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    memory_limit: str = DEFAULT_MEMORY_LIMIT,
    image: str = DEFAULT_IMAGE,
) -> SandboxResult:
    """Run a Python code string inside an isolated Docker container. Returns a SandboxResult."""
    client = _get_client()

    # write code to a temp file that we'll mount into the container
    run_id = uuid.uuid4().hex[:8]
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / f"script_{run_id}.py"
        script_path.write_text(code, encoding="utf-8")

        container = None
        try:
            container = client.containers.run(
                image=image,
                command=["python", f"/sandbox/{script_path.name}"],
                volumes={str(tmpdir): {"bind": "/sandbox", "mode": "ro"}},
                working_dir="/sandbox",
                network_disabled=True,
                mem_limit=memory_limit,
                cpu_quota=DEFAULT_CPU_QUOTA,
                detach=True,
                remove=False,  # we remove manually after reading logs
            )

            try:
                exit_status = container.wait(timeout=timeout)
                exit_code = exit_status.get("StatusCode")
                timed_out = False
            except Exception:
                # container.wait raised - most likely a timeout
                container.kill()
                exit_code = None
                timed_out = True

            logs = container.logs(stdout=True, stderr=False).decode("utf-8", errors="ignore")
            errs = container.logs(stdout=False, stderr=True).decode("utf-8", errors="ignore")

            return SandboxResult(
                stdout=logs,
                stderr=errs,
                exit_code=exit_code,
                timed_out=timed_out,
            )

        except ImageNotFound:
            return SandboxResult("", "", None, False, error=f"Docker image '{image}' not found. Run: docker pull {image}")
        except APIError as e:
            return SandboxResult("", "", None, False, error=f"Docker API error: {e}")
        except ContainerError as e:
            return SandboxResult("", str(e), e.exit_status, False)
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Run Python code safely inside a Docker sandbox.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a Python file to execute")
    group.add_argument("--code", help="Inline Python code string to execute")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()

    if args.file:
        code = Path(args.file).read_text(encoding="utf-8")
    else:
        code = args.code

    print("[sandbox] Running code in isolated container...\n")
    result = run_code_in_sandbox(code, timeout=args.timeout)

    if result.error:
        print(f"[sandbox] ERROR: {result.error}")
        return

    print(f"[sandbox] Exit code: {result.exit_code}")
    print(f"[sandbox] Timed out: {result.timed_out}")
    print("\n--- stdout ---")
    print(result.stdout or "(empty)")
    print("\n--- stderr ---")
    print(result.stderr or "(empty)")


if __name__ == "__main__":
    main()