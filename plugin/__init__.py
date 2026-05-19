"""
Investment Research Plugin for Hermes Agent.

Registers financial data tools into two isolated toolsets:
- investment-company: Stock-level data (for research group profiles)
- investment-market: Market/index/macro data (for investment committee profiles)

Physical isolation principle: research groups cannot see market data,
investment committee cannot see individual stock data.
"""

from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent


def _check_akshare_available() -> bool:
    try:
        import akshare  # noqa: F401
        return True
    except ImportError:
        return False


def register(ctx) -> None:
    """Called by Hermes plugin loader on startup."""
    from .tools.financial_data import (
        COMPANY_TOOLS,
        MARKET_TOOLS,
        SHARED_TOOLS,
    )
    from .tools.stock_pool import (
        POOL_COMPANY_TOOLS,
        POOL_SHARED_TOOLS,
    )

    # Financial data tools
    for name, schema, handler, description in COMPANY_TOOLS:
        ctx.register_tool(
            name=name,
            toolset="investment-company",
            schema=schema,
            handler=handler,
            check_fn=_check_akshare_available,
            description=description,
        )

    for name, schema, handler, description in MARKET_TOOLS:
        ctx.register_tool(
            name=name,
            toolset="investment-market",
            schema=schema,
            handler=handler,
            check_fn=_check_akshare_available,
            description=description,
        )

    for name, schema, handler, description in SHARED_TOOLS:
        ctx.register_tool(
            name=name,
            toolset="investment-company",
            schema=schema,
            handler=handler,
            check_fn=_check_akshare_available,
            description=description,
        )

    # Stock pool tools (always available, no akshare dependency)
    for name, schema, handler, description in POOL_COMPANY_TOOLS:
        ctx.register_tool(
            name=name,
            toolset="investment-company",
            schema=schema,
            handler=handler,
            description=description,
        )

    for name, schema, handler, description in POOL_SHARED_TOOLS:
        ctx.register_tool(
            name=name,
            toolset="investment-company",
            schema=schema,
            handler=handler,
            description=description,
        )

    # Register plugin skills
    skills_dir = _PLUGIN_DIR / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                ctx.register_skill(
                    name=skill_dir.name,
                    path=skill_dir / "SKILL.md",
                    description=f"Investment research: {skill_dir.name}",
                )
