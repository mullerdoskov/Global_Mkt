"""
cli.py
Interface de linha de comando para gerenciamento e ingestão de dados.
"""

import sys
import argparse

from backend.config.logging_config import setup_logging
from backend.db.connection import test_connection, engine
from backend.db.schema import create_all_tables
from backend.ingestion.loader import ingest_prices, update_prices
from backend.ingestion.fundamentals_loader import ingest_fundamentals
from backend.ingest_resumable import ingest_resumable, _reset_checkpoint

logger = setup_logging()


def command_db_init():
    """Inicializa o banco de dados."""
    logger.info("🔧 Inicializando banco de dados...")
    if test_connection():
        create_all_tables(engine)
        logger.info("✅ Banco inicializado com sucesso")
    else:
        logger.error("❌ Falha ao conectar ao banco")
        sys.exit(1)


def command_db_test():
    """Testa a conexão com o banco."""
    logger.info("🧪 Testando conexão...")
    if test_connection():
        logger.info("✅ Conexão OK")
    else:
        logger.error("❌ Falha na conexão")
        sys.exit(1)


def command_ingest_prices(args):
    """Ingere preços com pipeline padrão."""
    logger.info(f"📊 Iniciando ingestão de preços (período: {args.period})...")
    asset_types = args.types.split(",") if args.types else None
    success, errors = ingest_prices(period=args.period, asset_types=asset_types)
    logger.info(f"✅ Concluído: {success} sucesso, {errors} erros")


def command_update_prices(args):
    """Atualiza preços dos últimos N dias."""
    logger.info(f"🔄 Atualizando preços (últimos {args.days} dias)...")
    success, errors = update_prices(lookback_days=args.days)
    logger.info(f"✅ Concluído: {success} sucesso, {errors} erros")


def command_ingest_resumable(args):
    """Ingestão com checkpoint."""
    logger.info("📋 Ingestão resumível iniciada...")
    asset_types = args.types.split(",") if args.types else None
    ingest_resumable(asset_types=asset_types, period=args.period)
    logger.info("✅ Ingestão concluída")


def command_reset_checkpoint(args):
    """Reseta o checkpoint."""
    logger.info("🗑️  Resetando checkpoint...")
    _reset_checkpoint()
    logger.info("✅ Checkpoint resetado")


def command_ingest_fundamentals(args):
    """Ingere fundamentos."""
    logger.info("💰 Iniciando ingestão de fundamentos...")
    ingest_fundamentals()
    logger.info("✅ Ingestão de fundamentos concluída")


def main():
    """Main CLI."""
    parser = argparse.ArgumentParser(
        description="Market Platform Unified — CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python -m backend.cli db-init              # Inicializa banco de dados
  python -m backend.cli ingest-prices -p 90d # Ingere preços (90 dias)
  python -m backend.cli ingest-resumable     # Ingestão resumível
  python -m backend.cli reset-checkpoint     # Reseta progresso
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando")

    # db-init
    subparsers.add_parser("db-init", help="Inicializa banco de dados")

    # db-test
    subparsers.add_parser("db-test", help="Testa conexão com banco")

    # ingest-prices
    parser_prices = subparsers.add_parser("ingest-prices", help="Ingere preços")
    parser_prices.add_argument(
        "-p", "--period", default="90d",
        help="Período de dados (ex: 30d, 1y). Default: 90d"
    )
    parser_prices.add_argument(
        "-t", "--types",
        help="Tipos separados por vírgula (stock,index,commodity). Se omitido, ingere todos."
    )

    # update-prices
    parser_update = subparsers.add_parser("update-prices", help="Atualiza preços")
    parser_update.add_argument(
        "-d", "--days", type=int, default=5,
        help="Últimos N dias para atualizar. Default: 5"
    )

    # ingest-resumable
    parser_resumable = subparsers.add_parser("ingest-resumable", help="Ingestão com checkpoint")
    parser_resumable.add_argument(
        "-p", "--period", default="90d",
        help="Período de dados. Default: 90d"
    )
    parser_resumable.add_argument(
        "-t", "--types",
        help="Tipos separados por vírgula. Se omitido, ingere todos."
    )

    # reset-checkpoint
    subparsers.add_parser("reset-checkpoint", help="Reseta checkpoint de ingestão")

    # ingest-fundamentals
    subparsers.add_parser("ingest-fundamentals", help="Ingere dados de fundamentos")

    args = parser.parse_args()

    # Dispatch
    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "db-init":
            command_db_init()
        elif args.command == "db-test":
            command_db_test()
        elif args.command == "ingest-prices":
            command_ingest_prices(args)
        elif args.command == "update-prices":
            command_update_prices(args)
        elif args.command == "ingest-resumable":
            command_ingest_resumable(args)
        elif args.command == "reset-checkpoint":
            command_reset_checkpoint(args)
        elif args.command == "ingest-fundamentals":
            command_ingest_fundamentals(args)
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⏸️  Interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
