"""
Cliente yfinance com rate-limiting, backoff exponencial e User-Agent rotation.
Usa yf.download() em batch para evitar rate-limit do Yahoo Finance.
"""

import random
import time
from datetime import date, datetime

import yfinance as yf
import pandas as pd

from backend.config.settings import settings
from backend.config.logging_config import logger


class YFinanceClient:
    """Cliente resiliente para o Yahoo Finance via yfinance."""

    def __init__(self):
        self.rate_limit = settings.INGEST_RATE_LIMIT
        self.max_retries = settings.INGEST_MAX_RETRIES
        self.backoff_factor = settings.INGEST_BACKOFF_FACTOR
        self._last_request = 0.0
        self._consecutive_errors = 0

    def _wait_rate_limit(self):
        """Aguarda o intervalo mínimo entre requests, com cooldown adaptativo."""
        # Se muitos erros seguidos, aumentar espera
        extra_wait = min(self._consecutive_errors * 2, 30)
        total_wait = self.rate_limit + extra_wait

        elapsed = time.time() - self._last_request
        if elapsed < total_wait:
            time.sleep(total_wait - elapsed)
        self._last_request = time.time()

    def _on_success(self):
        """Reset do contador de erros consecutivos."""
        self._consecutive_errors = 0

    def _on_error(self):
        """Incrementa contador de erros consecutivos."""
        self._consecutive_errors += 1

    # ══════════════════════════════════════════════════════════
    #  BATCH DOWNLOAD (recomendado para ingestão em massa)
    # ══════════════════════════════════════════════════════════

    def fetch_prices_batch(
        self,
        symbols: list[str],
        start: str | date | None = None,
        end: str | date | None = None,
        period: str = "1y",
    ) -> dict[str, pd.DataFrame]:
        """
        Baixa preços OHLCV de MÚLTIPLOS símbolos em UMA chamada.
        yf.download() faz requests internos em paralelo com threads,
        o que é MUITO mais rápido e menos propenso a rate-limit
        do que chamar ticker.history() um por um.

        Args:
            symbols: Lista de tickers
            start: Data inicial (YYYY-MM-DD) ou None
            end: Data final (YYYY-MM-DD) ou None
            period: Período se start/end não fornecidos

        Returns:
            Dict[symbol] = DataFrame com colunas padronizadas
        """
        if not symbols:
            return {}

        result = {}
        logger.info(f"Batch download: {len(symbols)} símbolos via yf.download()")

        for attempt in range(1, self.max_retries + 1):
            try:
                self._wait_rate_limit()

                kwargs = {
                    "tickers": " ".join(symbols),
                    "auto_adjust": False,
                    "group_by": "ticker",
                    "threads": True,
                    "progress": False,
                }

                if start:
                    kwargs["start"] = str(start)
                    if end:
                        kwargs["end"] = str(end)
                else:
                    kwargs["period"] = period

                raw = yf.download(**kwargs)

                if raw.empty:
                    logger.warning(f"Batch download retornou vazio (tentativa {attempt})")
                    if attempt < self.max_retries:
                        self._backoff(attempt)
                        continue
                    return {}

                # Parsear resultado: se 1 símbolo, estrutura é diferente
                if len(symbols) == 1:
                    sym = symbols[0]
                    df = raw.copy()
                    df.index.name = "Date"
                    df = df.reset_index()
                    df = self._normalize_columns(df)
                    if not df.empty:
                        result[sym] = df
                else:
                    for sym in symbols:
                        try:
                            if sym in raw.columns.get_level_values(0):
                                df = raw[sym].dropna(how="all").copy()
                                df.index.name = "Date"
                                df = df.reset_index()
                                df = self._normalize_columns(df)
                                if not df.empty:
                                    result[sym] = df
                        except Exception as e:
                            logger.warning(f"[{sym}] Erro ao parsear batch: {e}")

                self._on_success()
                logger.info(f"Batch download: {len(result)}/{len(symbols)} com dados")
                return result

            except Exception as e:
                self._on_error()
                logger.error(f"Batch download erro (tentativa {attempt}): {e}")
                if attempt < self.max_retries:
                    self._backoff(attempt)

        return result

    # ══════════════════════════════════════════════════════════
    #  SINGLE DOWNLOAD (fallback)
    # ══════════════════════════════════════════════════════════

    def fetch_prices(
        self,
        symbol: str,
        start: str | date | None = None,
        end: str | date | None = None,
        period: str = "1y",
    ) -> pd.DataFrame:
        """
        Baixa preços OHLCV de UM símbolo.
        Para ingestão em massa, prefira fetch_prices_batch().
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                self._wait_rate_limit()

                kwargs = {
                    "tickers": symbol,
                    "auto_adjust": False,
                    "threads": False,
                    "progress": False,
                }
                if start:
                    kwargs["start"] = str(start)
                    if end:
                        kwargs["end"] = str(end)
                else:
                    kwargs["period"] = period

                df = yf.download(**kwargs)

                if df.empty:
                    logger.warning(f"[{symbol}] Sem dados (tentativa {attempt})")
                    if attempt < self.max_retries:
                        self._backoff(attempt)
                        continue
                    return pd.DataFrame()

                df.index.name = "Date"
                df = df.reset_index()
                df = self._normalize_columns(df)

                self._on_success()
                logger.info(f"[{symbol}] {len(df)} registros baixados")
                return df

            except Exception as e:
                self._on_error()
                logger.error(f"[{symbol}] Erro tentativa {attempt}/{self.max_retries}: {e}")
                if attempt < self.max_retries:
                    self._backoff(attempt)
                else:
                    logger.error(f"[{symbol}] Todas as tentativas falharam")
                    return pd.DataFrame()

        return pd.DataFrame()

    # ══════════════════════════════════════════════════════════
    #  INFO & FINANCIALS
    # ══════════════════════════════════════════════════════════

    def fetch_info(self, symbol: str) -> dict:
        """Baixa informações gerais do ticker (setor, market cap, etc)."""
        try:
            self._wait_rate_limit()
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            self._on_success()
            return info
        except Exception as e:
            self._on_error()
            logger.error(f"[{symbol}] Erro ao buscar info: {e}")
            return {}

    def fetch_financials(self, symbol: str) -> dict:
        """Baixa demonstrativos financeiros."""
        try:
            self._wait_rate_limit()
            ticker = yf.Ticker(symbol)
            result = {
                "income_stmt": getattr(ticker, "quarterly_income_stmt", pd.DataFrame()),
                "balance_sheet": getattr(ticker, "quarterly_balance_sheet", pd.DataFrame()),
                "cash_flow": getattr(ticker, "quarterly_cash_flow", pd.DataFrame()),
            }
            self._on_success()
            return result
        except Exception as e:
            self._on_error()
            logger.error(f"[{symbol}] Erro ao buscar financials: {e}")
            return {
                "income_stmt": pd.DataFrame(),
                "balance_sheet": pd.DataFrame(),
                "cash_flow": pd.DataFrame(),
            }

    # ══════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Garante colunas padronizadas."""
        # yfinance pode retornar MultiIndex nas colunas — flatten
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

        expected = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        for col in expected:
            if col not in df.columns:
                df[col] = None
        return df[expected]

    def _backoff(self, attempt: int):
        """Backoff exponencial com jitter — mais conservador."""
        base = self.backoff_factor ** attempt
        jitter = random.uniform(1, 3)
        wait = base + jitter + (self._consecutive_errors * 2)
        wait = min(wait, 60)  # cap em 60s
        logger.info(f"Backoff: aguardando {wait:.1f}s (tentativa {attempt}, erros_seguidos={self._consecutive_errors})")
        time.sleep(wait)


# Singleton
yf_client = YFinanceClient()
