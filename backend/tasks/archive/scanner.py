import asyncio
import logging
from typing import List, Dict
from datetime import datetime

from celery import Task
from .celery_app import celery_app
from backend.services.market.market_data_service import (
    market_data_service,
    POPULAR_STOCKS,
)

try:
    # Optional strategy import; provide fallback if unavailable
    from backend.core.strategies.atr_matrix import atr_matrix_strategy  # type: ignore
except Exception:  # pragma: no cover - fallback for non-critical optional module

    class _DummyAnalysis:
        def __init__(self):
            self.recommendation = "HOLD"
            self.confidence = 0.0
            self.overall_score = 0.0
            self.signals = []

    class _DummyStrategy:
        async def analyze(self, symbol: str, technical_data):
            return _DummyAnalysis()

    atr_matrix_strategy = _DummyStrategy()

try:
    from backend.services.notifications.discord_service import (
        discord_notifier,
    )
except Exception:

    class _NullNotifier:
        def is_configured(self) -> bool:
            return False

        async def send_scanner_results(self, *args, **kwargs):
            return None

        async def send_entry_signal(self, *args, **kwargs):
            return None

    discord_notifier = _NullNotifier()

logger = logging.getLogger(__name__)

# Use a subset for regular scanning to respect API limits
SCAN_UNIVERSE = POPULAR_STOCKS[:30]  # Top 30 stocks for regular scans


class AsyncTask(Task):
    """Custom Celery task class that supports async functions."""

    def __call__(self, *args, **kwargs):
        """Execute the task."""
        return asyncio.run(self.run_async(*args, **kwargs))

    async def run_async(self, *args, **kwargs):
        """Override this method in async tasks."""
        raise NotImplementedError


@celery_app.task(bind=True, base=AsyncTask)
async def run_atr_matrix_scan(self):
    """Run ATR Matrix scan for entry opportunities."""
    logger.info("Starting ATR Matrix scan...")
    start_time = datetime.now()

    try:
        # Run the scan
        results = await _scan_symbols_for_atr_matrix(SCAN_UNIVERSE)

        # Filter for entry opportunities
        entry_opportunities = [
            result
            for result in results
            if result.get("entry_signal") and result.get("confidence", 0) >= 0.6
        ]

        # Sort by ATR distance (closer to SMA50 is better)
        entry_opportunities.sort(key=lambda x: x.get("atr_distance", 999))

        scan_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"ATR Matrix scan completed: {len(entry_opportunities)} opportunities found in {scan_time:.1f}s"
        )

        # Send Discord notification
        if discord_notifier.is_configured() and entry_opportunities:
            top_picks = entry_opportunities[:5]
            await discord_notifier.send_scanner_results(
                scan_type="ATR Matrix Entry",
                total_scanned=len(SCAN_UNIVERSE),
                results_count=len(entry_opportunities),
                top_picks=[
                    {
                        "symbol": pick["symbol"],
                        "recommendation": "BUY",
                        "confidence": pick.get("confidence", 0),
                    }
                    for pick in top_picks
                ],
                scan_time=scan_time,
            )

            # Send individual entry signals for top picks
            for pick in top_picks[:3]:  # Top 3 only
                await discord_notifier.send_entry_signal(
                    symbol=pick["symbol"],
                    price=pick["current_price"],
                    atr_distance=pick.get("atr_distance", 0),
                    confidence=pick.get("confidence", 0),
                    reasons=pick.get("entry_reasons", []),
                    targets=pick.get("targets", []),
                    stop_loss=pick.get("stop_loss"),
                    risk_reward=pick.get("risk_reward"),
                    atr_value=pick.get("atr"),
                    rsi=pick.get("rsi"),
                    ma_alignment=pick.get("ma_alignment"),
                )

        return {
            "total_scanned": len(SCAN_UNIVERSE),
            "opportunities_found": len(entry_opportunities),
            "scan_time": scan_time,
            "top_picks": entry_opportunities[:10],
        }

    except Exception as e:
        logger.error(f"Error in ATR Matrix scan: {e}", exc_info=True)
        return {"error": str(e)}


@celery_app.task(bind=True, base=AsyncTask)
async def run_custom_scan(self, symbols: List[str], criteria: Dict):
    """Run a custom scan with specified criteria."""
    logger.info(f"Starting custom scan with {len(symbols)} symbols...")
    start_time = datetime.now()

    try:
        results = await _scan_symbols_with_criteria(symbols, criteria)
        scan_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Custom scan completed: {len(results)} results in {scan_time:.1f}s"
        )

        return {
            "total_scanned": len(symbols),
            "results_count": len(results),
            "scan_time": scan_time,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error in custom scan: {e}", exc_info=True)
        return {"error": str(e)}


@celery_app.task(bind=True, base=AsyncTask)
async def scan_single_symbol(self, symbol: str):
    """Analyze a single symbol with ATR Matrix strategy."""
    logger.info(f"Analyzing {symbol}...")

    try:
        # Get technical analysis
        technical_data = await market_data_service.get_technical_analysis(symbol)
        if not technical_data:
            return {"error": f"No data available for {symbol}"}

        # Run strategy analysis
        analysis = await atr_matrix_strategy.analyze(symbol, technical_data)

        return {
            "symbol": symbol,
            "current_price": technical_data.get("close", 0),
            "atr_distance": technical_data.get("atr_distance"),
            "atr_percent": technical_data.get("atr_percent"),
            "ma_aligned": technical_data.get("ma_aligned"),
            "recommendation": analysis.recommendation,
            "confidence": analysis.confidence,
            "signals": [
                {
                    "type": signal.signal_type,
                    "strength": signal.strength,
                    "metadata": signal.metadata,
                }
                for signal in analysis.signals
            ],
        }

    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
        return {"error": str(e)}


async def _scan_symbols_for_atr_matrix(symbols: List[str]) -> List[Dict]:
    """Internal function to scan symbols for ATR Matrix opportunities."""
    results = []

    # Process in batches to avoid overwhelming the API
    batch_size = 20
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]

        # Run analysis for batch
        batch_tasks = [_analyze_symbol_for_atr_matrix(symbol) for symbol in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        for symbol, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                logger.warning(f"Error analyzing {symbol}: {result}")
            elif result:
                results.append(result)

    return results


async def _analyze_symbol_for_atr_matrix(symbol: str) -> Dict:
    """Analyze a single symbol for ATR Matrix entry."""
    try:
        # Get technical data
        technical_data = await market_data_service.get_technical_analysis(symbol)
        if not technical_data:
            return None

        # Get current price (stock info not available with Alpha Vantage in same way)
        current_price = await market_data_service.get_current_price(symbol)

        # Run strategy analysis
        analysis = await atr_matrix_strategy.analyze(symbol, technical_data)

        # Check for entry signals
        entry_signals = [s for s in analysis.signals if s.signal_type == "ENTRY"]

        result = {
            "symbol": symbol,
            "name": symbol,  # Use symbol as name for now
            "current_price": technical_data.get("current_price", 0),
            "atr_distance": technical_data.get("atr_distance"),
            "atr_percent": technical_data.get("atr_percent"),
            "ma_alignment": technical_data.get("ma_alignment", False),
            "price_position_20d": technical_data.get("price_position_20d"),
            "recommendation": analysis.recommendation,
            "confidence": analysis.confidence,
            "overall_score": analysis.overall_score,
            "rsi": technical_data.get("rsi"),
            "atr": technical_data.get("atr"),
        }

        # Add entry signal details if present
        if entry_signals:
            entry_signal = entry_signals[0]
            result["entry_signal"] = True
            result["entry_reasons"] = entry_signal.metadata.get(
                "entry_reason", ""
            ).split("; ")
            result["stop_loss"] = entry_signal.stop_loss
            result["targets"] = entry_signal.metadata.get("all_targets", [])
            result["risk_reward"] = entry_signal.risk_reward_ratio
        else:
            result["entry_signal"] = False

        return result

    except Exception as e:
        logger.warning(f"Error analyzing {symbol}: {e}")
        return None


async def _scan_symbols_with_criteria(symbols: List[str], criteria: Dict) -> List[Dict]:
    """Scan symbols with custom criteria."""
    results = []

    # This would implement custom filtering logic based on criteria
    # For now, just run basic ATR Matrix analysis
    for symbol in symbols:
        try:
            result = await _analyze_symbol_for_atr_matrix(symbol)
            if result and _passes_custom_criteria(result, criteria):
                results.append(result)
        except Exception as e:
            logger.warning(f"Error scanning {symbol}: {e}")

    return results


def _passes_custom_criteria(result: Dict, criteria: Dict) -> bool:
    """Check if a result passes custom criteria."""
    # Implement custom filtering logic

    # ATR Distance filter
    if "max_atr_distance" in criteria:
        atr_distance = result.get("atr_distance")
        if atr_distance is None or atr_distance > criteria["max_atr_distance"]:
            return False

    if "min_atr_distance" in criteria:
        atr_distance = result.get("atr_distance")
        if atr_distance is None or atr_distance < criteria["min_atr_distance"]:
            return False

    # MA Alignment filter
    if criteria.get("require_ma_alignment"):
        if not result.get("ma_alignment"):
            return False

    # Confidence filter
    if "min_confidence" in criteria:
        if result.get("confidence", 0) < criteria["min_confidence"]:
            return False

    return True
