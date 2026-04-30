"""
api/export.py — ISSUE-017

Endpoint de exportação de série histórica em CSV.

GET /api/export/{symbol}.csv?period=<n><unidade>

Devolve uma `StreamingResponse` com `media_type="text/csv"`. Cabeçalho
`Content-Disposition: attachment; filename="<symbol>_<period>.csv"`
para forçar o download no navegador (cliente típico é o frontend
chamando via âncora `<a download>` ou abrindo a URL em nova aba).

Schema do CSV (1 cabeçalho + N linhas, ordem cronológica ascendente):

    date,open,high,low,close,adj_close,volume

Comportamento:
- `period` validado pelo mesmo `period_dep`/`parse_period` usado em
  `/api/prices/{symbol}/history` e `/api/prices/{symbol}/returns`
  (ISSUE-012). Formato inválido → 422 antes do streaming começar.
- Asset inexistente → 404. A checagem é feita ANTES de retornar a
  `StreamingResponse` para que o status HTTP final seja 404, não 200
  com corpo vazio.
- Sem preços no range → 200 com CSV de cabeçalho-apenas (1 linha).
  Decisão: a ausência de preços não é erro do cliente (o ativo existe
  e o período é válido); melhor devolver um CSV vazio do que 404, que
  semântica de "ativo não encontrado". A escolha é registrada em
  `DECISIONS.md`.
- Rate limit: 10/min/IP — mais agressivo que o default 60/min/IP. CSV
  é endpoint de extração (cliente típico: usuário humano clicando
  download). Sem limite mais apertado, vira vetor barato para varrer
  o histórico do banco. Configurável em `settings.rate_limit_export`.
- Streaming via generator: o handler emite linha por linha sem
  materializar a lista inteira em memória. Importante para períodos
  longos (10y × 252 dias úteis ≈ 2520 linhas — não é gigante, mas
  manter streaming é gratuito aqui).

Sem dependência de pandas — `csv.writer` da stdlib basta para a
serialização. `Decimal` (de `Numeric` do SQLAlchemy) vira string
diretamente; `None` vira string vazia.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from datetime import date, timedelta
from typing import Iterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from backend.api._limiter import limiter
from backend.api._periods import ParsedPeriod, period_dep
from backend.config.settings import settings
from backend.db.connection import get_session
from backend.db.schema import Asset, PriceDaily

router = APIRouter(prefix="/export", tags=["export"])

logger = logging.getLogger("market_platform")

CSV_HEADER = ["date", "open", "high", "low", "close", "adj_close", "volume"]

# Filename sanitization: símbolos como `^BVSP`, `BRL=X`, `PETR4.SA` precisam
# virar nome de arquivo seguro. Mantém alfanuméricos, ponto, underscore e
# hífen; troca o resto por underscore. Não estritamente necessário (o navegador
# tolera quase tudo entre aspas), mas evita surpresas em filesystems.
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename_part(value: str) -> str:
    """Sanitiza um pedaço de filename. Vazio → 'export' como fallback."""
    cleaned = _FILENAME_SAFE_RE.sub("_", value).strip("_")
    return cleaned or "export"


def _format_cell(value) -> str:
    """Converte um campo (Decimal/int/None) na string que vai pro CSV.

    `None` vira string vazia. Tudo o mais delega para `str(...)` —
    `Decimal('35.50')` vira `'35.50'`, `int(1234567)` vira `'1234567'`.
    `csv.writer` cuida do escape de vírgula/aspas/newline se aparecerem
    (não devem aparecer em valores numéricos, mas o writer é defensivo).
    """
    if value is None:
        return ""
    return str(value)


def _stream_prices_csv(rows: Iterator[PriceDaily]) -> Iterator[str]:
    """Gerador que emite o CSV linha a linha.

    Usa um `StringIO` reciclado por chunk: escreve no buffer, lê o que
    saiu, esvazia, repete. Isso evita acumular toda a saída antes do
    primeiro byte ir pro cliente.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    writer.writerow(CSV_HEADER)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    for price in rows:
        writer.writerow([
            price.date.isoformat() if price.date else "",
            _format_cell(price.open),
            _format_cell(price.high),
            _format_cell(price.low),
            _format_cell(price.close),
            _format_cell(price.adj_close),
            _format_cell(price.volume),
        ])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


@router.get("/{symbol}.csv")
@limiter.limit(settings.rate_limit_export)
def export_prices_csv(
    request: Request,
    symbol: str,
    period: ParsedPeriod = Depends(period_dep),
) -> StreamingResponse:
    """
    Exporta série histórica OHLCV de um ativo em formato CSV.

    Parâmetros:
    - symbol: símbolo do ativo (ex.: PETR4.SA, AAPL, ^BVSP).
    - period: período no formato `<n><d|w|m|y>`, range 1d..10y. Default 90d.
      Validação igual aos endpoints de prices (ver `_periods.parse_period`).

    Resposta: `200 OK` com `Content-Type: text/csv; charset=utf-8` e
    `Content-Disposition: attachment; filename="<symbol>_<period>.csv"`.
    Corpo: CSV com cabeçalho `date,open,high,low,close,adj_close,volume`
    seguido de uma linha por dia, em ordem cronológica ascendente.

    Erros:
    - 404 se `symbol` não existe na tabela `assets`.
    - 422 se `period` não casa com `<n><d|w|m|y>` ou está fora de 1d..10y.
    - 429 se o cliente excedeu `rate_limit_export` (default 10/min/IP).
    """
    session = get_session()
    try:
        asset = session.execute(
            select(Asset).where(Asset.symbol == symbol)
        ).scalar_one_or_none()

        if asset is None:
            raise HTTPException(
                status_code=404,
                detail=f"Asset '{symbol}' not found",
            )

        start_date = date.today() - timedelta(days=period.days)

        prices_query = (
            select(PriceDaily)
            .where(
                (PriceDaily.asset_id == asset.id)
                & (PriceDaily.date >= start_date)
            )
            .order_by(PriceDaily.date)
        )

        price_rows = session.execute(prices_query).scalars().all()

        logger.info(
            "export_csv: symbol=%s period=%s rows=%d",
            symbol, period.raw, len(price_rows),
        )

        filename = f"{_safe_filename_part(symbol)}_{_safe_filename_part(period.raw)}.csv"

        return StreamingResponse(
            _stream_prices_csv(iter(price_rows)),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    finally:
        session.close()
