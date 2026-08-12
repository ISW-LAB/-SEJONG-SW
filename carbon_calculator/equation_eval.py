# -*- coding: utf-8 -*-
"""
MATLAB 상대생장식 문자열을 안전하게 평가.

원본 MATLAB Carbon2 코드의 동작:
    evalStr = strrep(equationStr, 'X', num2str(X));
    if contains(evalStr, 'ln(Y)=')
        rhs = extractAfter(evalStr, 'ln(Y)=');
        Y = exp(eval(rhs));
    elseif contains(evalStr, 'Y=')
        rhs = extractAfter(evalStr, 'Y=');
        Y = eval(rhs);

Python 포팅 시 보안을 위해 `eval` 글로벌 네임스페이스를 제한하고,
MATLAB 의 `^` (거듭제곱) 을 `**` 로, `ln` 을 `math.log` 로 매핑한다.
"""
from __future__ import annotations

import math


# eval 환경에 노출할 허용 함수
_ALLOWED_FUNCS = {
    "ln": math.log,       # MATLAB ln → 자연로그
    "log": math.log,      # MATLAB log (Carbon2 식 일부에 사용)
    "exp": math.exp,
    "sqrt": math.sqrt,
    "pow": pow,
    "abs": abs,
}


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

    # eval 환경: 외부 변수/내장함수 차단, X(·H) 와 허용 함수만 노출
    env = {"__builtins__": {}}
    env.update(_ALLOWED_FUNCS)
    env["X"] = float(x)
    if h is not None:
        env["H"] = float(h)

    try:
        if "ln(Y)=" in eqn:
            rhs = eqn.split("ln(Y)=", 1)[1]
            return math.exp(eval(rhs, env))
        if "Y=" in eqn:
            rhs = eqn.split("Y=", 1)[1]
            return float(eval(rhs, env))
    except Exception as ex:
        raise EvaluationError(f"식 평가 실패: {equation_str!r} (X={x}): {ex}") from ex

    raise EvaluationError(f"인식할 수 없는 식 형식: {equation_str!r}")


class EvaluationError(Exception):
    pass
