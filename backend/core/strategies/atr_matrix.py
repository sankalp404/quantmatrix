from typing import Dict, List, Optional
from datetime import datetime
import math
from .base_strategy import BaseStrategy, SignalResult, StrategyAnalysis
from backend.config import settings

class ATRMatrixStrategy(BaseStrategy):
    """
    ATR Matrix Strategy implementation based on the TradingView script.
    
    This strategy uses ATR distance from SMA50 to generate entry and exit signals.
    Key components:
    - ATR distance calculation
    - Moving average alignment
    - Position in 20-day range
    - Risk/reward ratio calculation
    """
    
    def __init__(self):
        super().__init__("ATR Matrix")
        
        # Strategy parameters (configurable)
        self.set_parameter("atr_period", 14)
        self.set_parameter("entry_max_distance", 4.0)
        self.set_parameter("scale_out_levels", [7.0, 8.0, 9.0, 10.0])
        self.set_parameter("stop_loss_multiplier", 1.5)
        self.set_parameter("min_atr_percent", 3.0)  # Minimum ATR % for volatility
        self.set_parameter("min_price_position", 50.0)  # Min position in 20D range
        self.set_parameter("min_risk_reward", 3.0)  # Minimum R:R ratio
        self.set_parameter("max_position_size", 5.0)  # Max % of portfolio per position
    
    async def analyze(self, symbol: str, market_data: Dict) -> StrategyAnalysis:
        """
        Comprehensive ATR Matrix analysis for a symbol.
        """
        current_price = market_data.get('close', 0)
        timestamp = datetime.now()
        
        # Calculate ATR Matrix metrics
        technical_data = self._calculate_atr_matrix_metrics(market_data)
        
        # Generate signals
        signals = self.generate_signals(symbol, technical_data)
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(technical_data, current_price)
        
        # Overall assessment
        overall_score, recommendation, confidence = self._calculate_overall_assessment(technical_data)
        
        return StrategyAnalysis(
            symbol=symbol,
            current_price=current_price,
            timestamp=timestamp,
            strategy_name=self.name,
            signals=signals,
            technical_data=technical_data,
            risk_metrics=risk_metrics,
            overall_score=overall_score,
            recommendation=recommendation,
            confidence=confidence
        )
    
    def generate_signals(self, symbol: str, technical_data: Dict) -> List[SignalResult]:
        """Generate ATR Matrix trading signals."""
        signals = []
        timestamp = datetime.now()
        current_price = technical_data.get('close', 0)
        
        if not current_price:
            return signals
        
        # Entry Signal
        entry_signal = self._check_entry_conditions(technical_data)
        if entry_signal:
            # Calculate stop loss and targets
            stop_loss = self.calculate_stop_loss(symbol, current_price, technical_data)
            targets = self.calculate_targets(symbol, current_price, technical_data)
            
            # Calculate risk/reward for first target
            rr_ratio = 0
            if targets and stop_loss:
                rr_ratio = self.calculate_risk_reward_ratio(current_price, stop_loss, targets[0])
            
            signal = SignalResult(
                symbol=symbol,
                signal_type="ENTRY",
                strength=entry_signal['strength'],
                price=current_price,
                timestamp=timestamp,
                strategy_name=self.name,
                stop_loss=stop_loss,
                target_price=targets[0] if targets else None,
                risk_reward_ratio=rr_ratio,
                metadata={
                    'atr_distance': technical_data.get('atr_distance'),
                    'ma_aligned': technical_data.get('ma_aligned'),
                    'price_position_20d': technical_data.get('price_position_20d'),
                    'atr_percent': technical_data.get('atr_percent'),
                    'entry_reason': entry_signal['reason'],
                    'all_targets': targets
                }
            )
            signals.append(signal)
        
        # Scale-out signals
        scale_out_signals = self._check_scale_out_conditions(technical_data)
        for scale_signal in scale_out_signals:
            signal = SignalResult(
                symbol=symbol,
                signal_type="SCALE_OUT",
                strength=scale_signal['strength'],
                price=current_price,
                timestamp=timestamp,
                strategy_name=self.name,
                metadata={
                    'scale_level': scale_signal['level'],
                    'atr_distance': technical_data.get('atr_distance'),
                    'target_price': scale_signal['target_price'],
                    'scale_reason': scale_signal['reason']
                }
            )
            signals.append(signal)
        
        # Exit/Risk signals
        risk_signal = self._check_risk_conditions(technical_data)
        if risk_signal:
            signal = SignalResult(
                symbol=symbol,
                signal_type="EXIT",
                strength=risk_signal['strength'],
                price=current_price,
                timestamp=timestamp,
                strategy_name=self.name,
                metadata={
                    'exit_reason': risk_signal['reason'],
                    'urgency': risk_signal.get('urgency', 'MEDIUM')
                }
            )
            signals.append(signal)
        
        return signals
    
    def _check_entry_conditions(self, technical_data: Dict) -> Optional[Dict]:
        """Check if entry conditions are met."""
        atr_distance = technical_data.get('atr_distance')
        ma_aligned = technical_data.get('ma_aligned', False)
        price_position_20d = technical_data.get('price_position_20d', 0)
        atr_percent = technical_data.get('atr_percent', 0)
        close = technical_data.get('close', 0)
        sma_20 = technical_data.get('sma_20', 0)
        
        if not all([atr_distance is not None, close, sma_20]):
            return None
        
        # Core ATR Matrix entry conditions
        conditions_met = []
        strength = 0.0
        
        # 1. ATR Distance: Must be between 0 and 4
        if 0 <= atr_distance <= self.get_parameter("entry_max_distance"):
            conditions_met.append("ATR distance in buy zone")
            strength += 0.3
        else:
            return None  # This is a hard requirement
        
        # 2. Price above SMA20
        if close > sma_20:
            conditions_met.append("Price above SMA20")
            strength += 0.2
        else:
            return None  # This is a hard requirement
        
        # 3. Moving average alignment (highly preferred)
        if ma_aligned:
            conditions_met.append("Moving averages aligned")
            strength += 0.25
        
        # 4. Position in 20-day range (above 50%)
        if price_position_20d > self.get_parameter("min_price_position"):
            conditions_met.append(f"Strong position in 20D range ({price_position_20d:.1f}%)")
            strength += 0.15
        
        # 5. ATR volatility check
        if atr_percent >= self.get_parameter("min_atr_percent"):
            conditions_met.append(f"Sufficient volatility ({atr_percent:.2f}%)")
            strength += 0.1
        
        # Must meet minimum conditions to generate signal
        if strength >= 0.5:  # At least core conditions + some additional
            return {
                'strength': min(strength, 1.0),
                'reason': "; ".join(conditions_met),
                'conditions_met': len(conditions_met)
            }
        
        return None
    
    def _check_scale_out_conditions(self, technical_data: Dict) -> List[Dict]:
        """Check for scale-out opportunities."""
        signals = []
        atr_distance = technical_data.get('atr_distance')
        sma_50 = technical_data.get('sma_50')
        atr = technical_data.get('atr')
        
        if not all([atr_distance is not None, sma_50, atr]):
            return signals
        
        scale_levels = self.get_parameter("scale_out_levels")
        
        for level in scale_levels:
            if atr_distance >= level:
                target_price = sma_50 + (level * atr)
                
                # Calculate signal strength based on how far above the level we are
                overshoot = atr_distance - level
                strength = 0.7 + min(overshoot * 0.1, 0.3)  # Higher strength for bigger overshoots
                
                signals.append({
                    'level': level,
                    'strength': min(strength, 1.0),
                    'target_price': target_price,
                    'reason': f"ATR distance {atr_distance:.1f}x reached {level}x scale-out level"
                })
        
        return signals
    
    def _check_risk_conditions(self, technical_data: Dict) -> Optional[Dict]:
        """Check for risk/exit conditions."""
        close = technical_data.get('close', 0)
        sma_50 = technical_data.get('sma_50')
        atr_distance = technical_data.get('atr_distance')
        
        if not all([close, sma_50]):
            return None
        
        # Critical: Below SMA50
        if close < sma_50:
            return {
                'strength': 0.9,
                'reason': "Price below SMA50 - Risk Alert",
                'urgency': 'HIGH'
            }
        
        # High ATR distance (overextended)
        if atr_distance is not None and atr_distance > 10:
            return {
                'strength': 0.7,
                'reason': f"Overextended at {atr_distance:.1f}x ATR distance",
                'urgency': 'MEDIUM'
            }
        
        return None
    
    def calculate_position_size(
        self, 
        symbol: str, 
        price: float, 
        portfolio_value: float, 
        risk_per_trade: float = 0.02
    ) -> float:
        """Calculate position size based on ATR and portfolio risk."""
        if not price or not portfolio_value:
            return 0
        
        # Maximum position size as percentage of portfolio
        max_position_value = portfolio_value * (self.get_parameter("max_position_size") / 100)
        max_shares_by_size = max_position_value / price
        
        # Risk-based position sizing
        risk_amount = portfolio_value * risk_per_trade
        
        # For ATR-based position sizing, we need stop loss distance
        # Assuming 1.5x ATR stop loss for now (this could be refined with actual ATR data)
        estimated_stop_distance = price * 0.05  # Fallback: 5% stop loss
        
        shares_by_risk = risk_amount / estimated_stop_distance if estimated_stop_distance > 0 else 0
        
        # Take the smaller of the two constraints
        return min(max_shares_by_size, shares_by_risk)
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, technical_data: Dict) -> float:
        """Calculate ATR-based stop loss."""
        atr = technical_data.get('atr')
        stop_multiplier = self.get_parameter("stop_loss_multiplier")
        
        if not atr:
            # Fallback to percentage-based stop loss
            return entry_price * 0.95  # 5% stop loss
        
        stop_loss = entry_price - (stop_multiplier * atr)
        
        # Ensure stop loss is reasonable (not more than 10% below entry)
        min_stop = entry_price * 0.90
        return max(stop_loss, min_stop)
    
    def calculate_targets(self, symbol: str, entry_price: float, technical_data: Dict) -> List[float]:
        """Calculate ATR-based target prices."""
        sma_50 = technical_data.get('sma_50')
        atr = technical_data.get('atr')
        
        if not all([sma_50, atr]):
            # Fallback percentage targets
            return [
                entry_price * 1.07,  # 7% target
                entry_price * 1.10,  # 10% target
                entry_price * 1.15   # 15% target
            ]
        
        targets = []
        target_levels = [7, 10, 12]  # ATR multipliers for targets
        
        for level in target_levels:
            target = sma_50 + (level * atr)
            targets.append(target)
        
        return targets
    
    def _calculate_atr_matrix_metrics(self, market_data: Dict) -> Dict:
        """Calculate all ATR Matrix specific metrics."""
        result = market_data.copy()
        
        # ATR Distance calculation
        close = market_data.get('close')
        sma_50 = market_data.get('sma_50')
        atr = market_data.get('atr')
        
        if all([close, sma_50, atr]) and atr > 0:
            atr_distance = (close - sma_50) / atr
            result['atr_distance'] = atr_distance
            
            # ATR as percentage of price
            atr_percent = (atr / close) * 100
            result['atr_percent'] = atr_percent
        
        # MA Alignment check
        ema_10 = market_data.get('ema_10')
        sma_20 = market_data.get('sma_20')
        sma_100 = market_data.get('sma_100')
        sma_200 = market_data.get('sma_200')
        
        if all([ema_10, sma_20, sma_50, sma_100, sma_200]):
            ma_aligned = ema_10 >= sma_20 >= sma_50 >= sma_100 >= sma_200
            result['ma_aligned'] = ma_aligned
        
        return result
    
    def _calculate_risk_metrics(self, technical_data: Dict, current_price: float) -> Dict:
        """Calculate risk metrics for the position."""
        risk_metrics = {}
        
        # ATR-based risk
        atr = technical_data.get('atr')
        if atr and current_price:
            daily_risk_pct = (atr / current_price) * 100
            risk_metrics['daily_risk_percent'] = daily_risk_pct
            risk_metrics['risk_level'] = self._classify_risk_level(daily_risk_pct)
        
        # Distance from key levels
        sma_50 = technical_data.get('sma_50')
        if sma_50 and current_price:
            distance_from_support = ((current_price - sma_50) / current_price) * 100
            risk_metrics['support_distance_percent'] = distance_from_support
        
        # Volatility assessment
        atr_percent = technical_data.get('atr_percent', 0)
        risk_metrics['volatility_level'] = self._classify_volatility(atr_percent)
        
        return risk_metrics
    
    def _classify_risk_level(self, daily_risk_pct: float) -> str:
        """Classify risk level based on daily ATR."""
        if daily_risk_pct < 2:
            return "LOW"
        elif daily_risk_pct < 4:
            return "MEDIUM"
        elif daily_risk_pct < 6:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    def _classify_volatility(self, atr_percent: float) -> str:
        """Classify volatility level."""
        if atr_percent < 2:
            return "LOW"
        elif atr_percent < 4:
            return "MEDIUM"
        elif atr_percent < 6:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    def _calculate_overall_assessment(self, technical_data: Dict) -> tuple:
        """Calculate overall assessment score, recommendation, and confidence."""
        score = 0.0
        confidence = 0.0
        
        # ATR Distance (most important factor)
        atr_distance = technical_data.get('atr_distance')
        if atr_distance is not None:
            if 0 <= atr_distance <= 4:
                score += 0.4  # Strong buy zone
                confidence += 0.3
            elif 4 < atr_distance <= 7:
                score += 0.2  # Hold zone
                confidence += 0.2
            elif atr_distance > 7:
                score -= 0.2  # Scale out zone
                confidence += 0.3
            else:  # Below SMA50
                score -= 0.4
                confidence += 0.4
        
        # MA Alignment
        if technical_data.get('ma_aligned'):
            score += 0.25
            confidence += 0.2
        
        # Price position in 20D range
        price_pos = technical_data.get('price_position_20d', 0)
        if price_pos > 70:
            score += 0.15
            confidence += 0.1
        elif price_pos > 50:
            score += 0.1
            confidence += 0.1
        
        # ATR volatility
        atr_percent = technical_data.get('atr_percent', 0)
        if 3 <= atr_percent <= 6:
            score += 0.1
            confidence += 0.1
        elif atr_percent > 6:
            score -= 0.05  # Too volatile
        
        # Normalize scores
        score = max(0, min(1, score + 0.5))  # Shift to 0-1 range
        confidence = max(0, min(1, confidence))
        
        # Determine recommendation
        if score >= 0.7:
            recommendation = "BUY"
        elif score >= 0.6:
            recommendation = "HOLD"
        elif score >= 0.4:
            recommendation = "SCALE_OUT"
        else:
            recommendation = "SELL"
        
        return score, recommendation, confidence

# Global instance
atr_matrix_strategy = ATRMatrixStrategy() 