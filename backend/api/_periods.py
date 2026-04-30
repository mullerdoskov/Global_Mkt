"""
api/_periods.py — ISSUE-012

Validação estrita de strings de período usadas pelos endpoints
`/api/prices/{symbol}/history`, `/api/prices/{symbol}/returns` e
`/api/market/sectors`.

Antes desta issue, cada endpoint parseava `period` inline (ou via
`prices._parse_period`) e *silenciosamente* caía para 90 dias quando o
formato era desconhecido. Isso mascarava bugs no frontend (por exemplo,
um typo em `peridod=180d` virava silenciosamente "90 dias") e impedia
qualquer monitoramento de "uso indevido da API".

Comportamento novo: a única função pública `parse_period` aceita
`<inteiro positivo><unidade>` com unidade em {d, w, m, y}. Range válido
(após conversão para dias) é `[1, 3650]`, ou seja `1d..10y`. Qualquer
outra entrada levanta `HTTPException(422)` com mensagem de erro
explicando o formato esperado — o FastAPI converte em resposta JSON
estruturada, igual ao que faz para query params malformados.

`period_dep` é o wrapper para uso via `Depends(period_dep)` nos
handlers — declara `period` como `Query(...)` para a string aparecer
na OpenAPI e devolve um `ParsedPeriod` (frozen dataclass) com os dois
formatos: `raw` (string original, ecoada na resposta) e `delta`
(`timedelta` para cálculos de data).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from fastapi import HTTPException, Query, status

# Aceita "<inteiro>" + "<unidade>" com unidade em {d,w,m,y}. Não aceita
# espaço, sinal, ponto decimal, maiúsculas ou unidade extra.
_PERIOD_RE: Final = re.compile(r"^([1-9]\d*)([dwmy])$")

# Conversão de cada unidade para dias.
# `m` = 30 dias e `y` = 365 dias (aproximações comerciais — consistente
# com o comportamento anterior de prices._parse_period).
_UNIT_TO_DAYS: Final[dict[str, int]] = {"d": 1, "w": 7, "m": 30, "y": 365}

# Range válido em dias, inclusive nos dois extremos.
MIN_DAYS: Final = 1
MAX_DAYS: Final = 365 * 10  # 10y = 3650d

# Default usado pelos endpoints quando o cliente não passa `period`.
DEFAULT_PERIOD: Final = "90d"

# Mensagem reaproveitada em todas as situações de formato inválido.
_FORMAT_HINT: Final = (
    "Formato esperado: '<n><unidade>' com n inteiro positivo e unidade "
    "em {d, w, m, y}. Exemplos: '30d', '4w', '6m', '1y'. "
    f"Range permitido: '{MIN_DAYS}d' até '{MAX_DAYS // 365}y'."
)


@dataclass(frozen=True)
class ParsedPeriod:
    """
    Resultado de `parse_period`. `raw` é a string original (ex: '30d'),
    `delta` é o `timedelta` correspondente. `days` é açúcar para o
    cálculo `date.today() - timedelta(days=...)` que os handlers fazem.

    Frozen para que `repr(parsed)` seja estável — importante porque o
    `default_key_builder` da `fastapi-cache2` inclui `repr(kwargs)` na
    chave de cache, e dois requests com `period='90d'` precisam gerar
    a mesma chave.
    """

    raw: str
    delta: timedelta

    @property
    def days(self) -> int:
        return self.delta.days


def parse_period(period: str) -> ParsedPeriod:
    """
    Converte uma string `<n><unidade>` em `ParsedPeriod`.

    Aceita exatamente `<inteiro positivo><unidade>` com unidade em
    {d, w, m, y}, sem espaços, sem sinal, sem decimal. O resultado em
    dias precisa estar em `[MIN_DAYS, MAX_DAYS]` (inclusive).

    Levanta `HTTPException(422, ...)` com mensagem útil em qualquer
    outro caso. 422 é o mesmo status que o FastAPI usa para erros de
    validação de query params, mantendo a resposta consistente para o
    cliente.
    """
    if not isinstance(period, str) or not period:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"period vazio ou ausente. {_FORMAT_HINT}",
        )

    match = _PERIOD_RE.match(period)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"period inválido: {period!r}. {_FORMAT_HINT}",
        )

    qty = int(match.group(1))
    unit = match.group(2)
    days = qty * _UNIT_TO_DAYS[unit]

    if days < MIN_DAYS or days > MAX_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"period {period!r} fora do range permitido "
                f"({MIN_DAYS}d a {MAX_DAYS}d, inclusive). "
                f"Equivale a {days} dias."
            ),
        )

    return ParsedPeriod(raw=period, delta=timedelta(days=days))


def period_dep(
    period: str = Query(
        DEFAULT_PERIOD,
        description=(
            "Período no formato '<n><unidade>' com unidade em "
            "{d, w, m, y}. Exemplos: '30d', '4w', '6m', '1y'. "
            f"Range permitido: '{MIN_DAYS}d'..'{MAX_DAYS // 365}y'."
        ),
        examples=["30d", "4w", "6m", "1y"],
    ),
) -> ParsedPeriod:
    """
    Wrapper FastAPI-friendly para uso com `Depends(period_dep)`.

    Mantém `period` como `Query(...)` para que apareça no OpenAPI / Swagger
    com descrição e exemplos, e delega a validação para `parse_period`.
    Qualquer 422 levantado por `parse_period` propaga até o cliente.
    """
    return parse_period(period)
