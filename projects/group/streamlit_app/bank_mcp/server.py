"""MCP server for local bank transfer beneficiary checking and risk reporting."""

from __future__ import annotations

import argparse
import logging
from functools import lru_cache

from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from .db import BankReviewRepository, DEFAULT_DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)

mcp = FastMCP(
    "Bank Transfer Review MCP",
    instructions=(
        "Local SQLite-backed MCP server for BANK TRANSFER REVIEW. "
        "Use these tools to check beneficiary name/account alignment "
        "and prior scam-risk reports before approving a bank transfer, "
        "and to report risky beneficiary accounts discovered during bank "
        "transfer review or fraud operations."
    ),
    json_response=True,
)


@lru_cache(maxsize=1)
def repository() -> BankReviewRepository:
    repo = BankReviewRepository(DEFAULT_DB_PATH)
    repo.initialize()
    log.info("Bank transfer review SQLite ready at %s", repo.db_path)
    return repo


@mcp.tool()
def check_beneficiary_for_bank_transfer(
    recipient_name: str,
    account_number: str,
) -> dict[str, str]:
    """Check a bank transfer beneficiary using recipient name and account number for bank transfer review."""
    result = repository().check_beneficiary(
        recipient_name=recipient_name,
        account_number=account_number,
    )
    return result.to_dict()


@mcp.tool()
def report_beneficiary_risk_for_bank_transfer(
    account_number: str,
    reason_code: str,
    recipient_name: str | None = None,
    case_id: str | None = None,
) -> dict[str, str]:
    """Report a bank transfer beneficiary as suspicious using beneficiary account number and optional recipient name."""
    result = repository().report_beneficiary_risk(
        account_number=account_number,
        recipient_name=recipient_name,
        reason_code=reason_code,
        case_id=case_id,
    )
    return result.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the local BANK TRANSFER REVIEW MCP server."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host for the bank transfer review MCP HTTP server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port for the bank transfer review MCP HTTP server.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport to run for the bank transfer review server.",
    )
    args = parser.parse_args()
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    repository()
    if args.transport == "streamable-http":
        app = CORSMiddleware(
            mcp.streamable_http_app(),
            allow_origins=["*"],
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["Mcp-Session-Id"],
        )
        uvicorn.run(app, host=args.host, port=args.port)
        return
    mcp.run()


if __name__ == "__main__":
    main()
