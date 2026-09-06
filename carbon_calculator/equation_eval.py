# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""
MATLAB 상대생장식 문자열을 허용목록 기반으로 안전하게 평가.

원본 MATLAB Carbon2 코드의 동작:
    evalStr = strrep(equationStr, 'X', num2str(X));
    if contains(evalStr, 'ln(Y)=')
        rhs = extractAfter(evalStr, 'ln(Y)=');
        Y = exp(eval(rhs));
    elseif contains(evalStr, 'Y=')
        rhs = extractAfter(evalStr, 'Y=');
        Y = eval(rhs);

Python 포팅에서는 ``eval`` 을 사용하지 않는다. 식을 추상 구문 트리로
파싱한 뒤 숫자, X/H, 기본 산술 연산, 허용 함수만 재귀적으로 계산한다.
MATLAB 의 `^` (거듭제곱) 은 `**` 로 변환한다.
"""
from __future__ import annotations

import ast
import math
import operator

from .i18n import tr


# 수식 라이브러리에서 사용할 수 있는 함수와 연산자.
_ALLOWED_FUNCS = {
    "ln": math.log,       # MATLAB ln → 자연로그
    "log": math.log,      # MATLAB log (Carbon2 식 일부에 사용)
    "exp": math.exp,
    "sqrt": math.sqrt,
    "pow": pow,
    "abs": abs,
}

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _evaluate_node(node: ast.AST, variables: dict[str, float]) -> float:
    """허용된 AST 노드만 계산한다."""
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body, variables)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("numeric constants only")
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise ValueError(f"unknown variable: {node.id}")
        return float(variables[node.id])
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_node(node.left, variables)
        right = _evaluate_node(node.right, variables)
        return float(_BINARY_OPERATORS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return float(_UNARY_OPERATORS[type(node.op)](_evaluate_node(node.operand, variables)))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise ValueError("function is not permitted")
        if node.keywords:
            raise ValueError("keyword arguments are not permitted")
        args = [_evaluate_node(arg, variables) for arg in node.args]
        return float(_ALLOWED_FUNCS[node.func.id](*args))
    raise ValueError(f"expression element is not permitted: {type(node).__name__}")


def _evaluate_rhs(rhs: str, variables: dict[str, float]) -> float:
    tree = ast.parse(rhs, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 100:
        raise ValueError("expression is too complex")
    result = _evaluate_node(tree, variables)
    if not math.isfinite(result):
        raise ValueError("result is not finite")
    return result


def _matlab_to_python(equation: str) -> str:
    """MATLAB 식을 Python 식으로 변환."""
    # ^ → **  (MATLAB 거듭제곱 → Python 거듭제곱)
    return equation.replace("^", "**")


def evaluate(equation_str: str, x: float, h: float | None = None) -> float:
    """
    상대생장식을 평가하여 바이오매스 Y 반환.

    Args:
        equation_str: 예) "Y=0.063*X^2.578"  또는  "ln(Y)=2.43*ln(X)-2.28"
                      다변수 식은 두 번째 변수로 `H` 를 사용. 예) "Y=exp(-4.7483+1.7395*ln(X*H))"
        x: 첫 번째 변수 (DBH cm 등)
        h: 두 번째 변수 (수고 H·밀도·LAI 등). 단일변수 식이면 None.

    Returns:
        Y 값 (바이오매스). 평가 실패 시 EvaluationError 예외.
    """
    eqn = _matlab_to_python(equation_str.strip())

    variables = {"X": float(x)}
    if h is not None:
        variables["H"] = float(h)

    try:
        if eqn.startswith("ln(Y)="):
            return math.exp(_evaluate_rhs(eqn[len("ln(Y)="):], variables))
        if eqn.startswith("Y="):
            return _evaluate_rhs(eqn[len("Y="):], variables)
    except Exception as ex:
        raise EvaluationError(
            tr("식 평가 실패: {equation!r} (X={x}): {error}")
            .format(equation=equation_str, x=x, error=ex)) from ex

    raise EvaluationError(
        tr("인식할 수 없는 식 형식: {equation!r}").format(equation=equation_str))


class EvaluationError(Exception):
    pass
