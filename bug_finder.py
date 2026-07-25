"""
bug_finder.py
Runs static analysis (pylint) on a Python file, then sends the results
plus the actual code to an LLM to summarize, prioritize, and explain
real bugs vs. style noise.

Usage:
    python bug_finder.py --file indexer.py
    python bug_finder.py --file indexer.py --model phi3
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

BUG_SYSTEM_PROMPT = """You are a senior code reviewer analyzing static analysis output for real bugs.

You will be given:
1. The raw source code of a file
2. Static analysis warnings from pylint (JSON format)

Your job:
- Identify which warnings represent REAL bugs or risks (logic errors, unhandled exceptions,
  undefined variables, security issues) vs. which are just STYLE noise (naming conventions,
  missing docstrings, line length).
- Group your response into two sections: "Real Issues" and "Style Notes" (style notes can be brief/skipped if none).
- For each real issue, cite the line number and explain WHY it matters and a suggested fix in 1-2 sentences.
- If pylint found nothing but you notice a real risk in the code yourself, add it under Real Issues too.
- Be concise. No preamble, no "here is the analysis" - just the two sections.
"""


def run_pylint(filepath: str) -> list[dict]:
    """Run pylint on a file and return parsed JSON output. Returns [] if pylint unavailable."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pylint", filepath, "--output-format=json", "--disable=C0114,C0115,C0116"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        print("[bug_finder] pylint not installed. Run: pip install pylint")
        return []
    except subprocess.TimeoutExpired:
        print("[bug_finder] pylint timed out on this file.")
        return []

    output = result.stdout.strip()
    if not output:
        return []

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        print("[bug_finder] Could not parse pylint output.")
        return []


def format_pylint_findings(findings: list[dict]) -> str:
    if not findings:
        return "No pylint warnings found."
    lines = []
    for f in findings:
        lines.append(
            f"Line {f.get('line')}: [{f.get('symbol')}] {f.get('message')}"
        )
    return "\n".join(lines)


def analyze_file(filepath: str, model: str = "phi3") -> str:
    path = Path(filepath)
    if not path.exists():
        return f"File not found: {filepath}"

    source = path.read_text(encoding="utf-8", errors="ignore")
    findings = run_pylint(str(path))
    findings_text = format_pylint_findings(findings)

    user_prompt = f"""Source code ({path.name}):
```python
{source}
```

Pylint findings:
{findings_text}

Analyze this and respond in the required two-section format."""

    llm = ChatOllama(model=model, base_url=OLLAMA_BASE_URL, temperature=0.1)
    messages = [
        SystemMessage(content=BUG_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    return response.content


def main():
    parser = argparse.ArgumentParser(description="Find bugs in a Python file using static analysis + LLM.")
    parser.add_argument("--file", required=True, help="Path to the Python file to analyze")
    parser.add_argument("--model", default="phi3", help="Ollama model to use")
    args = parser.parse_args()

    print(f"[bug_finder] Analyzing {args.file} ...\n")
    result = analyze_file(args.file, model=args.model)
    print(result)


if __name__ == "__main__":
    main()