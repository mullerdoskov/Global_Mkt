"""
ingest_resumable.py
Ingestão com checkpoint — retoma exatamente onde parou.
Salva progresso em logs/checkpoint.txt.
"""

import os
import sys
import time
import argparse
import logging
from datetime import datetime

from backend.config.logging_config import setup_logging
from backend.config.symbols import SYMBOLS_BY_TYPE
from backend.ingestion.yf_client import YFinanceClient, BATCH_SIZE
from backend.ingestion.loader import ensure_asset_exists, upsert_prices, log_ingestion
from backend.db.connection import get_session
from backend.db.schema import IngestionStatus

logger = setup_logging()

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "logs")
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "checkpoint.txt")


def _load_checkpoint() -> set:
    """Carrega checkpoint — retorna set de símbolos já processados."""
    if not os.path.exists(CHECKPOINT_FILE):
        return set()
    with open(CHECKPOINT_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def _save_checkpoint(symbol: str):
    """Adiciona símbolo ao checkpoint."""
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(f"{symbol}\n")


def _reset_checkpoint():
    """Apaga o checkpoint para recomeçar do zero."""
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        logger.info("🗑️  Checkpoint resetado.")
    else:
        logger.info("ℹ️  Nenhum checkpoint para resetar.")


def ingest_resumable(asset_types: list[str] = None, period: str = "90d"):
    """
    Ingestão com checkpoint. Pode ser parada e retomada.

    Args:
        asset_types: Lista de tipos (stock, index, etc.). None = todos.
        period: Período de dados (default: 90 dias).
    """
    client = YFinanceClient()
    completed = _load_checkpoint()

    if asset_types is None:
        asset_types = list(SYMBOLS_BY_TYPE.keys())

    # Monta lista total de (tipo, símbolo) respeitando checkpoint
    tasks = []
    for at in asset_types:
        for symbol in SYMBOLS_BY_TYPE.get(at, []):
            if symbol not in completed:
                tasks.append((at, symbol))

    total = sum(len(SYMBOLS_BY_TYPE.get(at, [])) for at in asset_types)
    remaining = len(tasks)
    already_done = total - remaining

    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 INGESTÃO RESUMÍVEL")
    logger.info(f"   Total: {total} | Já feitos: {already_done} | Restantes: {remaining}")
    logger.info(f"   Tipos: {asset_types}")
    logger.info(f"   Período: {period}")
    logger.info(f"{'='*60}\n")

    if remaining == 0:
        logger.info("✅ Todos os tickers já foram processados! Use --reset para recomeçar.")
        return

    success_count = 0
    error_count = 0
    current_type = None

    for i, (asset_type, symbol) in enumerate(tasks):
        # Log mudança de tipo
        if asset_type != current_type:
            if current_type is not None:
                client.sleep_between_types()
            current_type = asset_type
            type_symbols = [s for t, s in tasks[i:] if t == asset_type]
            logger.info(f"\n📂 {asset_type.upper()} — {len(type_symbols)} restantes")

        # Log batch
        if i % BATCH_SIZE == 0 and i > 0:
            client.sleep_between_batches()

        start_time = time.time()
        session = get_session()

        try:
            asset_id = ensure_asset_exists(session, symbol, asset_type, client)
            df = client.download_prices(symbol, period=period)

            if df is not None and not df.empty:
                rows = upsert_prices(session, asset_id, df)
                duration = time.time() - start_time
                log_ingestion(session, symbol, "prices", rows,
                              IngestionStatus.success, duration=duration)
                success_count += 1
                progress = already_done + success_count + error_count
                pct = (progress / total) * 100
                logger.info(f"✅ [{progress}/{total} {pct:.1f}%] {symbol}: {rows} preços — {duration:.1f}s")
            else:
                log_ingestion(session, symbol, "prices", 0,
                              IngestionStatus.error, "Sem dados")
                error_count += 1
                logger.warning(f"⚠️  {symbol}: sem dados")

            _save_checkpoint(symbol)

        except KeyboardInterrupt:
            logger.info(f"\n⏸️  Interrompido pelo usuário. Progresso salvo no checkpoint.")
            logger.info(f"   Para retomar: python ingest_resumable.py")
            session.close()
            sys.exit(0)

        except Exception as e:
            duration = time.time() - start_time
            log_ingestion(session, symbol, "prices", 0,
                          IngestionStatus.error, str(e)[:500], duration)
            error_count += 1
            logger.error(f"❌ {symbol}: {e}")
            _save_checkpoint(symbol)  # Marca como processado mesmo com erro

        finally:
            session.close()

    logger.info(f"\n{'='*60}")
    logger.info(f"🏁 INGESTÃO CONCLUÍDA")
    logger.info(f"   ✅ Sucesso: {success_count}")
    logger.info(f"   ❌ Erros: {error_count}")
    logger.info(f"   📊 Total processado: {already_done + success_count + error_count}/{total}")
    logger.info(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Ingestão resumível de preços de mercado")
    parser.add_argument("--type", choices=["stock", "index", "commodity", "fx", "crypto"],
                        help="Tipo de ativo para ingerir (default: todos)")
    parser.add_argument("--period", default="90d",
                        help="Período de dados (default: 90d)")
    parser.add_argument("--reset", action="store_true",
                        help="Apaga checkpoint e recomeça do zero")
    args = parser.parse_args()

    if args.reset:
        _reset_checkpoint()
        return

    types = [args.type] if args.type else None
    ingest_resumable(asset_types=types, period=args.period)


if __name__ == "__main__":
    main()
