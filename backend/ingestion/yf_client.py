"""
ingestion/yf_client.py
Cliente yfinance com rate-limit, backoff exponencial e rotação de User-Agent.
Compatível com yfinance >= 0.2.40 (curl_cffi backend).
"""

import time
import random
import logging
import yfinance as yf

logger = logging.getLogger("market_platform")

# ══════════════════════════════════════════════
# CONFIGURAÇÕES DE RATE-LIMIT
# ══════════════════════════════════════════════
REQUESTS_PER_MINUTE = 8
SLEEP_BETWEEN_REQUESTS = 60.0 / REQUESTS_PER_MINUTE  # ~7.5s
SLEEP_BETWEEN_BATCHES = 12  # segundos
SLEEP_BETWEEN_TYPES = 30   # segundos entre tipos de ativo
MAX_BACKOFF = 360           # 6 minutos máximo de backoff
BATCH_SIZE = 5              # tickers por batch

# ══════════════════════════════════════════════
# USER-AGENTS ROTATIVOS
# ══════════════════════════════════════════════
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]


def _rotate_user_agent():
    """Seleciona um User-Agent aleatório."""
    return random.choice(USER_AGENTS)


class YFinanceClient:
    """Cliente yfinance com proteção contra rate-limit."""

    def __init__(self):
        """
        Inicializa o cliente sem sessão customizada.
        yfinance >= 0.2.40 usa curl_cffi internamente, incompatível com requests-cache.
        O rate-limit é feito via sleep entre requisições.
        """
        self._request_count = 0
        self._last_request_time = 0

    def _rate_limit(self):
        """Aplica rate-limit entre requisições."""
        elapsed = time.time() - self._last_request_time
        if elapsed < SLEEP_BETWEEN_REQUESTS:
            sleep_time = SLEEP_BETWEEN_REQUESTS - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()
        self._request_count += 1

    def _backoff(self, attempt: int) -> float:
        """Calcula tempo de espera com backoff exponencial + jitter."""
        wait = min(MAX_BACKOFF, (2 ** attempt) * 15 + random.uniform(0, 5))
        logger.warning(f"⏳ Backoff: aguardando {wait:.1f}s (tentativa {attempt + 1})")
        time.sleep(wait)
        return wait

    def get_ticker(self, symbol: str) -> yf.Ticker:
        """Retorna um objeto Ticker do yfinance (sem sessão customizada)."""
        self._rate_limit()
        return yf.Ticker(symbol)

    def download_prices(self, symbol: str, period: str = "90d",
                        interval: str = "1d", max_retries: int = 3):
        """
        Baixa preços OHLCV para um ticker.

        Args:
            symbol: Ticker do ativo.
            period: Período de dados (default: 90 dias).
            interval: Intervalo (default: diário).
            max_retries: Máximo de tentativas com backoff.

        Returns:
            DataFrame com preços ou None em caso de erro.
        """
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                data = yf.download(
                    symbol,
                    period=period,
                    interval=interval,
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
                if data is not None and not data.empty:
                    logger.info(f"📊 {symbol}: {len(data)} registros baixados")
                    return data
                else:
                    logger.warning(f"⚠️  {symbol}: sem dados retornados")
                    return None
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate" in error_str or "too many" in error_str:
                    self._backoff(attempt)
                else:
                    logger.error(f"❌ {symbol}: erro na tentativa {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        return None
        return None

    def get_info(self, symbol: str, max_retries: int = 3) -> dict:
        """Retorna informações do ticker (nome, setor, market_cap, etc.)."""
        for attempt in range(max_retries):
            try:
                ticker = self.get_ticker(symbol)
                info = ticker.info
                if info:
                    return info
            except Exception as e:
                if "429" in str(e).lower():
                    self._backoff(attempt)
                else:
                    logger.error(f"❌ {symbol} info: {e}")
                    if attempt >= max_retries - 1:
                        return {}
        return {}

    def get_financials(self, symbol: str, max_retries: int = 3) -> dict:
        """
        Retorna dados financeiros: income_stmt, balance_sheet, cashflow.

        Returns:
            Dict com chaves: income_stmt, balance_sheet, cashflow (DataFrames).
        """
        for attempt in range(max_retries):
            try:
                ticker = self.get_ticker(symbol)
                return {
                    "income_stmt": ticker.quarterly_income_stmt,
                    "balance_sheet": ticker.quarterly_balance_sheet,
                    "cashflow": ticker.quarterly_cashflow,
                }
            except Exception as e:
                if "429" in str(e).lower():
                    self._backoff(attempt)
                else:
                    logger.error(f"❌ {symbol} financials: {e}")
                    if attempt >= max_retries - 1:
                        return {}
        return {}

    @staticmethod
    def sleep_between_batches():
        """Pausa entre batches de tickers."""
        logger.info(f"💤 Pausa entre batches: {SLEEP_BETWEEN_BATCHES}s")
        time.sleep(SLEEP_BETWEEN_BATCHES)

    @staticmethod
    def sleep_between_types():
        """Pausa mais longa entre tipos de ativo."""
        logger.info(f"💤 Pausa entre tipos: {SLEEP_BETWEEN_TYPES}s")
        time.sleep(SLEEP_BETWEEN_TYPES)
