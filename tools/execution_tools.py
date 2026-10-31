"""
Execution Tools for Computational and Data Processing Tasks.
"""

import ast
import json
import operator
from datetime import datetime, timezone
from typing import Any

from core.logger import get_agent_logger
from tools.tool_registry import ToolPermissionLevel, ToolRegistry

logger = get_agent_logger("tools.execution_tools")

# Allowed operators for safe mathematical evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
    elif isinstance(node, ast.UnaryOp):
        operand = _safe_eval(node.operand)
        op_type = type(node.op)
        if op_type in SAFE_OPERATORS:
            return SAFE_OPERATORS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    else:
        raise ValueError(f"Disallowed expression node: {type(node).__name__}")


def calculate_expression(expression: str) -> dict[str, Any]:
    """
    Safely evaluate a mathematical or arithmetic expression without using eval().

    Args:
        expression: Mathematical string (e.g., '100 * (1 - 0.05) + 12.5').
    """
    clean_expr = expression.strip()
    try:
        parsed = ast.parse(clean_expr, mode="eval")
        result = _safe_eval(parsed.body)
        return {
            "expression": clean_expr,
            "result": result,
            "status": "computed",
        }
    except Exception as exc:
        return {
            "expression": clean_expr,
            "error": f"Evaluation error: {exc}",
            "status": "failed",
        }


def format_data_table(headers: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    """
    Format tabular data into a structured Markdown representation.
    """
    if not headers or not rows:
        return {"markdown_table": "", "row_count": 0}

    header_line = "| " + " | ".join(str(h) for h in headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = ["| " + " | ".join(str(item) for item in row) + " |" for row in rows]

    table_md = "\n".join([header_line, separator_line] + row_lines)
    return {
        "markdown_table": table_md,
        "row_count": len(rows),
        "column_count": len(headers),
    }


def register_execution_tools(registry: ToolRegistry) -> None:
    """Register execution tools into registry."""
    registry.register(
        name="calculate_expression",
        description="Safely compute mathematical calculations and financial formulas.",
        handler=calculate_expression,
        parameters={"expression": {"type": "string", "required": True}},
        permission_level=ToolPermissionLevel.SAFE_EXECUTION,
    )
    registry.register(
        name="format_data_table",
        description="Format list data and records into structured Markdown tables.",
        handler=format_data_table,
        parameters={
            "headers": {"type": "array", "required": True},
            "rows": {"type": "array", "required": True},
        },
        permission_level=ToolPermissionLevel.SAFE_EXECUTION,
    )
