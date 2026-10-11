"""
Code_agent.py
Compatibility facade for services.code_agent.
Preserves backward-compatibility while adopting snake_case naming.
"""

from services.code_agent import (
    CodeAgentState,
    run_agent,
    build_graph,
    generate_code_node,
    execute_code_node,
    should_retry,
    main,
)

__all__ = [
    "CodeAgentState",
    "run_agent",
    "build_graph",
    "generate_code_node",
    "execute_code_node",
    "should_retry",
    "main",
]

if __name__ == "__main__":
    main()