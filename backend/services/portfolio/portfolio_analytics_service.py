#!/usr/bin/env python3
"""
Portfolio Analytics Service - Snowball Analytics Style
Provides comprehensive portfolio analysis, performance metrics, and insights.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

try:
    from backend.models.position import Position
    from backend.models.tax_lot import TaxLot
    from backend.models.transaction import Transaction
    from backend.services.clients.ibkr_client import ibkr_client
    from backend.services.clients.ibkr_flexquery_client import flexquery_client
except ImportError:
    pass

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetrics:
    """Portfolio performance and risk metrics."""

    total_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float

    # Performance Metrics
    ytd_return: float
    total_return: float
    annualized_return: float

    # Risk Metrics
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    beta: float

    # Asset Allocation
    equity_allocation: float
    options_allocation: float
    cash_allocation: float

    # Tax Information
    long_term_positions: int
    short_term_positions: int
    unrealized_lt_gains: float
    unrealized_st_gains: float
    tax_loss_harvest_opportunities: float


@dataclass
class TaxOptimizationOpportunity:
    """Tax optimization opportunity."""

    symbol: str
    opportunity_type: str  # "tax_loss_harvest", "ltcg_realization", "wash_sale_warning"
    market_value: float
    unrealized_pnl: float
    days_held: int
    estimated_tax_impact: float
    recommendation: str
    confidence: float


class PortfolioAnalyticsService:
    """
    Portfolio Analytics Service - Professional grade portfolio analysis.

    Provides Snowball Analytics-style functionality:
    - Portfolio performance & risk metrics
    - Tax optimization opportunities
    - Asset allocation analysis
    - Performance attribution
    - Risk monitoring
    """

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session

    async def get_portfolio_analytics(self, account_id: str) -> Dict[str, Any]:
        """
        Get comprehensive portfolio analytics for account.

        Returns Snowball Analytics-style dashboard data.
        """
        try:
            logger.info(f"📊 Generating portfolio analytics for {account_id}")

            # Get current positions from IBKR
            positions = await ibkr_client.get_positions(account_id)

            # Get official tax lots from FlexQuery
            tax_lots = await flexquery_client.get_official_tax_lots(account_id)

            # Calculate metrics
            metrics = await self._calculate_portfolio_metrics(positions, tax_lots)

            # Find tax optimization opportunities
            tax_opportunities = await self._find_tax_opportunities(tax_lots)

            # Asset allocation analysis
            allocation = self._calculate_asset_allocation(positions)

            # Performance attribution
            performance = await self._calculate_performance_attribution(
                positions, tax_lots
            )

            return {
                "account_id": account_id,
                "as_of_date": datetime.now().isoformat(),
                "portfolio_metrics": metrics.__dict__,
                "tax_opportunities": [opp.__dict__ for opp in tax_opportunities],
                "asset_allocation": allocation,
                "performance_attribution": performance,
                "positions_count": len(positions),
                "tax_lots_count": len(tax_lots),
            }

        except Exception as e:
            logger.error(f"❌ Error in portfolio analytics: {e}")
            return {"error": str(e)}

    async def _calculate_portfolio_metrics(
        self, positions: List[Dict], tax_lots: List[Dict]
    ) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics."""

        # Basic totals
        total_value = sum(pos.get("market_value", 0) for pos in positions)
        total_cost_basis = sum(lot.get("cost_basis", 0) for lot in tax_lots)
        total_unrealized_pnl = total_value - total_cost_basis
        total_unrealized_pnl_pct = (
            (total_unrealized_pnl / total_cost_basis * 100)
            if total_cost_basis > 0
            else 0
        )

        # Asset allocation
        equity_value = sum(
            pos.get("market_value", 0)
            for pos in positions
            if pos.get("contract_type") == "STK"
        )
        options_value = sum(
            pos.get("market_value", 0)
            for pos in positions
            if pos.get("contract_type") == "OPT"
        )

        equity_allocation = (equity_value / total_value * 100) if total_value > 0 else 0
        options_allocation = (
            (options_value / total_value * 100) if total_value > 0 else 0
        )
        cash_allocation = max(0, 100 - equity_allocation - options_allocation)

        # Tax lot analysis
        long_term_positions = len(
            [lot for lot in tax_lots if lot.get("is_long_term", False)]
        )
        short_term_positions = len(tax_lots) - long_term_positions

        unrealized_lt_gains = sum(
            lot.get("unrealized_pnl", 0)
            for lot in tax_lots
            if lot.get("is_long_term", False) and lot.get("unrealized_pnl", 0) > 0
        )
        unrealized_st_gains = sum(
            lot.get("unrealized_pnl", 0)
            for lot in tax_lots
            if not lot.get("is_long_term", False) and lot.get("unrealized_pnl", 0) > 0
        )

        # Calculate tax loss harvest opportunities
        tax_loss_harvest_opportunities = sum(
            abs(lot.get("unrealized_pnl", 0))
            for lot in tax_lots
            if lot.get("unrealized_pnl", 0) < -1000
        )  # $1000+ losses

        # Performance metrics (simplified - would need historical data for accurate calculation)
        ytd_return = total_unrealized_pnl_pct  # Simplified
        total_return = total_unrealized_pnl_pct  # Simplified
        annualized_return = total_return / max(1, len(tax_lots) / 252)  # Rough estimate

        # Risk metrics (simplified - would need price history)
        volatility = 15.0  # Default estimate
        sharpe_ratio = (
            max(0, annualized_return - 2.0) / volatility
        )  # Assuming 2% risk-free rate
        max_drawdown = min(
            0,
            (
                min(lot.get("unrealized_pnl_pct", 0) for lot in tax_lots)
                if tax_lots
                else 0
            ),
        )
        beta = 1.0  # Default market beta

        return PortfolioMetrics(
            total_value=total_value,
            total_cost_basis=total_cost_basis,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_pct=total_unrealized_pnl_pct,
            ytd_return=ytd_return,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            beta=beta,
            equity_allocation=equity_allocation,
            options_allocation=options_allocation,
            cash_allocation=cash_allocation,
            long_term_positions=long_term_positions,
            short_term_positions=short_term_positions,
            unrealized_lt_gains=unrealized_lt_gains,
            unrealized_st_gains=unrealized_st_gains,
            tax_loss_harvest_opportunities=tax_loss_harvest_opportunities,
        )

    async def _find_tax_opportunities(
        self, tax_lots: List[Dict]
    ) -> List[TaxOptimizationOpportunity]:
        """Find tax optimization opportunities."""
        opportunities = []

        for lot in tax_lots:
            symbol = lot.get("symbol", "")
            unrealized_pnl = lot.get("unrealized_pnl", 0)
            days_held = lot.get("days_held", 0)
            current_value = lot.get("market_value", 0)

            # Tax loss harvesting opportunity
            if unrealized_pnl < -1000:  # $1000+ loss
                estimated_tax_savings = (
                    abs(unrealized_pnl) * 0.24
                )  # Assume 24% tax rate

                opportunities.append(
                    TaxOptimizationOpportunity(
                        symbol=symbol,
                        opportunity_type="tax_loss_harvest",
                        market_value=current_value,
                        unrealized_pnl=unrealized_pnl,
                        days_held=days_held,
                        estimated_tax_impact=estimated_tax_savings,
                        recommendation=f"Consider harvesting ${abs(unrealized_pnl):,.0f} loss for tax savings",
                        confidence=0.8,
                    )
                )

            # Long-term capital gains opportunity (approaching 1 year)
            elif 300 <= days_held <= 365 and unrealized_pnl > 0:
                opportunities.append(
                    TaxOptimizationOpportunity(
                        symbol=symbol,
                        opportunity_type="ltcg_opportunity",
                        market_value=current_value,
                        unrealized_pnl=unrealized_pnl,
                        days_held=days_held,
                        estimated_tax_impact=0,
                        recommendation=f"Wait {365 - days_held} days for long-term capital gains treatment",
                        confidence=0.9,
                    )
                )

            # Wash sale warning (if we had transaction history)
            # This would require checking for recent sales of the same security

        return opportunities

    def _calculate_asset_allocation(self, positions: List[Dict]) -> Dict[str, Any]:
        """Calculate detailed asset allocation."""
        total_value = sum(pos.get("market_value", 0) for pos in positions)

        if total_value == 0:
            return {"error": "No positions found"}

        # By asset class
        by_asset_class = {}
        for pos in positions:
            asset_class = pos.get("contract_type", "UNKNOWN")
            value = pos.get("market_value", 0)

            if asset_class not in by_asset_class:
                by_asset_class[asset_class] = {"value": 0, "percentage": 0}

            by_asset_class[asset_class]["value"] += value

        # Calculate percentages
        for asset_class in by_asset_class:
            by_asset_class[asset_class]["percentage"] = (
                by_asset_class[asset_class]["value"] / total_value * 100
            )

        # Top holdings
        top_holdings = sorted(
            [
                {
                    "symbol": pos.get("symbol"),
                    "value": pos.get("market_value", 0),
                    "percentage": pos.get("market_value", 0) / total_value * 100,
                }
                for pos in positions
            ],
            key=lambda x: x["value"],
            reverse=True,
        )[:10]

        return {
            "total_value": total_value,
            "by_asset_class": by_asset_class,
            "top_holdings": top_holdings,
            "concentration_risk": max(
                [h["percentage"] for h in top_holdings], default=0
            ),
        }

    async def _calculate_performance_attribution(
        self, positions: List[Dict], tax_lots: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate performance attribution by various factors."""

        # By security
        by_security = {}
        for lot in tax_lots:
            symbol = lot.get("symbol", "")
            unrealized_pnl = lot.get("unrealized_pnl", 0)

            if symbol not in by_security:
                by_security[symbol] = 0
            by_security[symbol] += unrealized_pnl

        # Top contributors and detractors
        sorted_performance = sorted(
            by_security.items(), key=lambda x: x[1], reverse=True
        )
        top_contributors = sorted_performance[:5]
        top_detractors = sorted_performance[-5:]

        return {
            "by_security": by_security,
            "top_contributors": [{"symbol": s, "pnl": p} for s, p in top_contributors],
            "top_detractors": [{"symbol": s, "pnl": p} for s, p in top_detractors],
            "total_securities": len(by_security),
        }


# Global service instance
portfolio_analytics_service = PortfolioAnalyticsService()
