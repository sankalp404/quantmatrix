import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from backend.services.market_data import market_data_service
from backend.core.strategies.atr_matrix import atr_matrix_strategy

logger = logging.getLogger(__name__)

class PortfolioAlertsService:
    """Service for generating portfolio-specific alerts for current holdings."""
    
    async def generate_portfolio_alerts(self, positions: List[Dict]) -> List[Dict]:
        """Generate alerts for current portfolio positions."""
        alerts = []
        
        if not positions:
            return alerts
        
        # Process positions concurrently
        alert_tasks = [self._analyze_position_for_alerts(position) for position in positions]
        position_alerts = await asyncio.gather(*alert_tasks, return_exceptions=True)
        
        for alert_list in position_alerts:
            if isinstance(alert_list, list):
                alerts.extend(alert_list)
            elif isinstance(alert_list, Exception):
                logger.error(f"Error generating alerts: {alert_list}")
        
        # Sort by priority (most urgent first)
        sorted_alerts = sorted(alerts, key=lambda x: self._get_alert_priority(x), reverse=True)
        
        return sorted_alerts[:10]  # Return top 10 most important alerts
    
    async def _analyze_position_for_alerts(self, position: Dict) -> List[Dict]:
        """Analyze a single position for relevant alerts."""
        alerts = []
        symbol = position.get('symbol', '')
        current_price = position.get('current_price', 0)
        avg_cost = position.get('avg_cost', 0)
        quantity = position.get('quantity', 0)
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0)
        position_value = position.get('position_value', 0)
        
        if not symbol or not current_price:
            return alerts
        
        try:
            # Get technical analysis for the position
            technical_data = await market_data_service.get_technical_analysis(symbol)
            if not technical_data:
                return alerts
            
            # Run ATR Matrix strategy analysis
            strategy_analysis = await atr_matrix_strategy.analyze(symbol, technical_data)
            
            # 1. Entry/Scale-In Opportunities
            entry_alerts = self._check_entry_opportunities(symbol, position, strategy_analysis, technical_data)
            alerts.extend(entry_alerts)
            
            # 2. Scale-Out/Take Profit Alerts
            scale_out_alerts = self._check_scale_out_opportunities(symbol, position, strategy_analysis, technical_data)
            alerts.extend(scale_out_alerts)
            
            # 3. Risk Management Alerts
            risk_alerts = self._check_risk_alerts(symbol, position, strategy_analysis, technical_data)
            alerts.extend(risk_alerts)
            
            # 4. Technical Pattern Alerts
            technical_alerts = self._check_technical_alerts(symbol, position, technical_data)
            alerts.extend(technical_alerts)
            
        except Exception as e:
            logger.error(f"Error analyzing position {symbol}: {e}")
        
        return alerts
    
    def _check_entry_opportunities(self, symbol: str, position: Dict, strategy_analysis, technical_data: Dict) -> List[Dict]:
        """Check for additional entry/scale-in opportunities."""
        alerts = []
        current_price = position.get('current_price', 0)
        avg_cost = position.get('avg_cost', 0)
        
        # Look for ATR Matrix entry signals below average cost (DCA opportunity)
        for signal in strategy_analysis.signals:
            if signal.signal_type == "ENTRY":
                if current_price < avg_cost * 0.95:  # 5% below average cost
                    alerts.append({
                        'symbol': symbol,
                        'alert_type': 'DCA_OPPORTUNITY',
                        'priority': 'high',
                        'message': f"DCA opportunity: {symbol} at ${current_price:.2f} (5%+ below avg cost ${avg_cost:.2f})",
                        'action': 'BUY',
                        'target_price': current_price,
                        'confidence': signal.strength,
                        'atr_distance': technical_data.get('atr_distance'),
                        'reasoning': 'ATR Matrix entry signal below average cost provides good DCA opportunity'
                    })
        
        return alerts
    
    def _check_scale_out_opportunities(self, symbol: str, position: Dict, strategy_analysis, technical_data: Dict) -> List[Dict]:
        """Check for scale-out opportunities."""
        alerts = []
        current_price = position.get('current_price', 0)
        avg_cost = position.get('avg_cost', 0)
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0)
        atr_distance = technical_data.get('atr_distance', 0)
        atr_value = technical_data.get('atr', 0)
        sma_50 = technical_data.get('sma_50', 0)
        
        # ATR-based scale-out levels
        if atr_value and sma_50:
            distance_from_sma50 = abs(current_price - sma_50) / atr_value
            
            scale_out_levels = [
                (7.0, 25, "First scale-out"),
                (8.0, 25, "Second scale-out"), 
                (9.0, 25, "Third scale-out"),
                (10.0, 25, "Final scale-out")
            ]
            
            for level, percentage, description in scale_out_levels:
                if distance_from_sma50 >= level:
                    alerts.append({
                        'symbol': symbol,
                        'alert_type': 'SCALE_OUT',
                        'priority': 'high',
                        'message': f"{description}: {symbol} at {level:.1f}x ATR distance (${current_price:.2f})",
                        'action': 'SELL',
                        'percentage': percentage,
                        'target_price': current_price,
                        'atr_distance': distance_from_sma50,
                        'reasoning': f'Price reached {level}x ATR distance from SMA50, triggering {description.lower()}'
                    })
                    break  # Only trigger the first applicable level
        
        # Percentage-based scale-out for significant gains
        if unrealized_pnl_pct >= 20:
            alerts.append({
                'symbol': symbol,
                'alert_type': 'PROFIT_TAKING',
                'priority': 'medium',
                'message': f"Consider profit taking: {symbol} up {unrealized_pnl_pct:.1f}%",
                'action': 'SELL',
                'percentage': 25,
                'target_price': current_price,
                'reasoning': f'Strong unrealized gain of {unrealized_pnl_pct:.1f}% suggests taking some profits'
            })
        
        return alerts
    
    def _check_risk_alerts(self, symbol: str, position: Dict, strategy_analysis, technical_data: Dict) -> List[Dict]:
        """Check for risk management alerts."""
        alerts = []
        current_price = position.get('current_price', 0)
        avg_cost = position.get('avg_cost', 0)
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0)
        sma_50 = technical_data.get('sma_50', 0)
        atr_value = technical_data.get('atr', 0)
        rsi = technical_data.get('rsi', 50)
        
        # Stop loss alerts
        if unrealized_pnl_pct <= -8:
            alerts.append({
                'symbol': symbol,
                'alert_type': 'STOP_LOSS',
                'priority': 'critical',
                'message': f"Stop loss consideration: {symbol} down {abs(unrealized_pnl_pct):.1f}%",
                'action': 'SELL',
                'target_price': current_price,
                'reasoning': f'Position down {abs(unrealized_pnl_pct):.1f}%, consider cutting losses'
            })
        
        # Price below SMA50 alert
        if current_price < sma_50:
            alerts.append({
                'symbol': symbol,
                'alert_type': 'TECHNICAL_BREAK',
                'priority': 'high',
                'message': f"Technical breakdown: {symbol} below SMA50 (${sma_50:.2f})",
                'action': 'REVIEW',
                'target_price': sma_50,
                'reasoning': 'Price broke below key SMA50 support level'
            })
        
        # Oversold condition
        if rsi < 30:
            alerts.append({
                'symbol': symbol,
                'alert_type': 'OVERSOLD',
                'priority': 'medium',
                'message': f"Oversold condition: {symbol} RSI at {rsi:.1f}",
                'action': 'BUY',
                'target_price': current_price,
                'reasoning': f'RSI of {rsi:.1f} indicates oversold condition, potential bounce opportunity'
            })
        
        # Overbought condition
        elif rsi > 70:
            alerts.append({
                'symbol': symbol,
                'alert_type': 'OVERBOUGHT',
                'priority': 'medium',
                'message': f"Overbought condition: {symbol} RSI at {rsi:.1f}",
                'action': 'SELL',
                'target_price': current_price,
                'reasoning': f'RSI of {rsi:.1f} indicates overbought condition, potential pullback ahead'
            })
        
        return alerts
    
    def _check_technical_alerts(self, symbol: str, position: Dict, technical_data: Dict) -> List[Dict]:
        """Check for technical pattern alerts."""
        alerts = []
        current_price = position.get('current_price', 0)
        
        # Moving average alignment changes
        ema_10 = technical_data.get('ema_10', 0)
        sma_20 = technical_data.get('sma_20', 0)
        sma_50 = technical_data.get('sma_50', 0)
        sma_100 = technical_data.get('sma_100', 0)
        sma_200 = technical_data.get('sma_200', 0)
        
        ma_aligned = (ema_10 >= sma_20 >= sma_50 >= sma_100 >= sma_200) if all([ema_10, sma_20, sma_50, sma_100, sma_200]) else False
        
        if ma_aligned:
            alerts.append({
                'symbol': symbol,
                'alert_type': 'MA_ALIGNMENT',
                'priority': 'low',
                'message': f"Bullish MA alignment: {symbol} all moving averages aligned",
                'action': 'HOLD',
                'target_price': current_price,
                'reasoning': 'All moving averages are bullishly aligned (EMA10≥SMA20≥SMA50≥SMA100≥SMA200)'
            })
        
        # Volume analysis would go here if we had volume data
        
        return alerts
    
    def _get_alert_priority(self, alert: Dict) -> int:
        """Get numeric priority for sorting alerts."""
        priority_map = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return priority_map.get(alert.get('priority', 'low'), 1)
    
    def format_alerts_for_discord(self, alerts: List[Dict]) -> str:
        """Format alerts for Discord message."""
        if not alerts:
            return "✅ **No immediate action items** - All positions looking good!"
        
        formatted_alerts = []
        
        # Group by priority
        critical_alerts = [a for a in alerts if a.get('priority') == 'critical']
        high_alerts = [a for a in alerts if a.get('priority') == 'high']
        medium_alerts = [a for a in alerts if a.get('priority') == 'medium']
        
        if critical_alerts:
            formatted_alerts.append("🚨 **CRITICAL ALERTS**")
            for alert in critical_alerts[:3]:
                formatted_alerts.append(f"• {alert['message']}")
            formatted_alerts.append("")
        
        if high_alerts:
            formatted_alerts.append("⚠️ **HIGH PRIORITY**")
            for alert in high_alerts[:3]:
                formatted_alerts.append(f"• {alert['message']}")
            formatted_alerts.append("")
        
        if medium_alerts and len(formatted_alerts) < 10:
            formatted_alerts.append("📋 **WATCH LIST**")
            for alert in medium_alerts[:2]:
                formatted_alerts.append(f"• {alert['message']}")
        
        return "\n".join(formatted_alerts)

# Global instance
portfolio_alerts_service = PortfolioAlertsService() 