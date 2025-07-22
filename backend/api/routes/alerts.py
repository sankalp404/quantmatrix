from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta

from backend.models import get_db
from backend.models.alert import Alert, AlertCondition, AlertTemplate, AlertHistory
from backend.models.user import User
from backend.services.market_data import market_data_service

router = APIRouter()

# Pydantic models
class AlertConditionCreate(BaseModel):
    condition_type: str  # PRICE, ATR_DISTANCE, RSI, MACD, etc.
    operator: str       # GT, LT, EQ, CROSSES_ABOVE, CROSSES_BELOW
    target_value: float
    indicator_params: Optional[Dict[str, Any]] = None
    timeframe: str = "1D"
    logical_operator: str = "AND"
    group_id: Optional[int] = None

class AlertCreate(BaseModel):
    name: str
    description: Optional[str] = None
    symbol: str
    alert_type: str  # PRICE, INDICATOR, SIGNAL, PORTFOLIO
    is_repeating: bool = False
    max_triggers: int = 1
    notify_discord: bool = True
    notify_email: bool = False
    notify_app: bool = True
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    expires_at: Optional[datetime] = None
    custom_message: Optional[str] = None
    conditions: List[AlertConditionCreate]

class AlertUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_repeating: Optional[bool] = None
    max_triggers: Optional[int] = None
    notify_discord: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_app: Optional[bool] = None
    priority: Optional[str] = None
    expires_at: Optional[datetime] = None
    custom_message: Optional[str] = None

class AlertConditionResponse(BaseModel):
    id: int
    condition_type: str
    operator: str
    target_value: float
    current_value: Optional[float]
    is_met: bool
    times_met: int
    last_checked: Optional[datetime]
    
    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    symbol: str
    alert_type: str
    is_active: bool
    is_repeating: bool
    max_triggers: int
    current_triggers: int
    priority: str
    created_at: datetime
    last_triggered: Optional[datetime]
    expires_at: Optional[datetime]
    conditions: List[AlertConditionResponse]
    
    class Config:
        from_attributes = True

class AlertTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    template_config: Dict[str, Any]
    usage_count: int
    
    class Config:
        from_attributes = True

class QuickAlertCreate(BaseModel):
    symbol: str
    alert_type: str  # "price_above", "price_below", "atr_entry", "atr_scale_out"
    value: Optional[float] = None

@router.post("/", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Create a new alert."""
    # Create alert
    alert = Alert(
        user_id=user_id,
        name=alert_data.name,
        description=alert_data.description,
        symbol=alert_data.symbol.upper(),
        alert_type=alert_data.alert_type,
        is_repeating=alert_data.is_repeating,
        max_triggers=alert_data.max_triggers,
        notify_discord=alert_data.notify_discord,
        notify_email=alert_data.notify_email,
        notify_app=alert_data.notify_app,
        priority=alert_data.priority,
        expires_at=alert_data.expires_at,
        custom_message=alert_data.custom_message
    )
    
    db.add(alert)
    db.flush()  # Get the alert ID
    
    # Create conditions
    for condition_data in alert_data.conditions:
        condition = AlertCondition(
            alert_id=alert.id,
            condition_type=condition_data.condition_type,
            operator=condition_data.operator,
            target_value=condition_data.target_value,
            indicator_params=condition_data.indicator_params,
            timeframe=condition_data.timeframe,
            logical_operator=condition_data.logical_operator,
            group_id=condition_data.group_id
        )
        db.add(condition)
    
    db.commit()
    db.refresh(alert)
    
    return alert

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    user_id: int = 1,  # TODO: Get from JWT token
    active_only: bool = False,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get user's alerts."""
    query = db.query(Alert).filter(Alert.user_id == user_id)
    
    if active_only:
        query = query.filter(Alert.is_active == True)
    
    if symbol:
        query = query.filter(Alert.symbol == symbol.upper())
    
    alerts = query.order_by(Alert.created_at.desc()).all()
    return alerts

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Get a specific alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return alert

@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Update an alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Update fields
    update_data = alert_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    db.commit()
    db.refresh(alert)
    
    return alert

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Delete an alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    db.delete(alert)
    db.commit()
    
    return {"message": "Alert deleted successfully"}

@router.post("/quick", response_model=AlertResponse)
async def create_quick_alert(
    quick_alert: QuickAlertCreate,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Create a quick alert using preset templates."""
    symbol = quick_alert.symbol.upper()
    
    # Get current market data for context
    technical_data = await market_data_service.get_technical_analysis(symbol)
    current_price = technical_data.get('close', 0) if technical_data else 0
    
    if quick_alert.alert_type == "price_above":
        target_price = quick_alert.value or (current_price * 1.05)  # 5% above if not specified
        
        alert = Alert(
            user_id=user_id,
            name=f"{symbol} Price Above ${target_price:.2f}",
            symbol=symbol,
            alert_type="PRICE",
            priority="MEDIUM"
        )
        
        condition = AlertCondition(
            condition_type="PRICE",
            operator="GT",
            target_value=target_price
        )
        
    elif quick_alert.alert_type == "price_below":
        target_price = quick_alert.value or (current_price * 0.95)  # 5% below if not specified
        
        alert = Alert(
            user_id=user_id,
            name=f"{symbol} Price Below ${target_price:.2f}",
            symbol=symbol,
            alert_type="PRICE",
            priority="HIGH"
        )
        
        condition = AlertCondition(
            condition_type="PRICE",
            operator="LT",
            target_value=target_price
        )
        
    elif quick_alert.alert_type == "atr_entry":
        alert = Alert(
            user_id=user_id,
            name=f"{symbol} ATR Matrix Entry Setup",
            symbol=symbol,
            alert_type="SIGNAL",
            priority="MEDIUM",
            custom_message="ATR Matrix entry opportunity detected!"
        )
        
        condition = AlertCondition(
            condition_type="ATR_DISTANCE",
            operator="LT",
            target_value=4.0  # ATR distance less than 4x
        )
        
    elif quick_alert.alert_type == "atr_scale_out":
        scale_level = quick_alert.value or 7.0
        
        alert = Alert(
            user_id=user_id,
            name=f"{symbol} ATR {scale_level}x Scale Out",
            symbol=symbol,
            alert_type="SIGNAL",
            priority="HIGH",
            custom_message=f"Time to scale out at {scale_level}x ATR!"
        )
        
        condition = AlertCondition(
            condition_type="ATR_DISTANCE",
            operator="GT",
            target_value=scale_level
        )
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid alert type"
        )
    
    # Save to database
    db.add(alert)
    db.flush()
    
    condition.alert_id = alert.id
    db.add(condition)
    
    db.commit()
    db.refresh(alert)
    
    return alert

@router.get("/templates/", response_model=List[AlertTemplateResponse])
async def get_alert_templates(db: Session = Depends(get_db)):
    """Get available alert templates."""
    templates = db.query(AlertTemplate).filter(
        AlertTemplate.is_public == True
    ).order_by(AlertTemplate.usage_count.desc()).all()
    
    return templates

@router.post("/templates/{template_id}/use", response_model=AlertResponse)
async def use_alert_template(
    template_id: int,
    symbol: str,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Create an alert from a template."""
    template = db.query(AlertTemplate).filter(
        AlertTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Create alert from template configuration
    config = template.template_config
    
    alert = Alert(
        user_id=user_id,
        name=config.get('name', '').replace('{symbol}', symbol),
        description=template.description,
        symbol=symbol.upper(),
        alert_type=config.get('alert_type', 'INDICATOR'),
        priority=config.get('priority', 'MEDIUM'),
        custom_message=config.get('custom_message', '').replace('{symbol}', symbol)
    )
    
    db.add(alert)
    db.flush()
    
    # Create conditions from template
    for condition_config in config.get('conditions', []):
        condition = AlertCondition(
            alert_id=alert.id,
            condition_type=condition_config['condition_type'],
            operator=condition_config['operator'],
            target_value=condition_config['target_value'],
            indicator_params=condition_config.get('indicator_params'),
            timeframe=condition_config.get('timeframe', '1D')
        )
        db.add(condition)
    
    # Increment usage count
    template.usage_count += 1
    
    db.commit()
    db.refresh(alert)
    
    return alert

@router.get("/history/", response_model=List[Dict])
async def get_alert_history(
    user_id: int = 1,  # TODO: Get from JWT token
    limit: int = 50,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get alert trigger history."""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    history = db.query(AlertHistory).join(Alert).filter(
        Alert.user_id == user_id,
        AlertHistory.triggered_at >= cutoff_date
    ).order_by(AlertHistory.triggered_at.desc()).limit(limit).all()
    
    return [
        {
            "id": h.id,
            "alert_id": h.alert_id,
            "triggered_at": h.triggered_at,
            "trigger_price": float(h.trigger_price) if h.trigger_price else None,
            "condition_met": h.condition_met,
            "message_title": h.message_title,
            "message_body": h.message_body,
            "discord_sent": h.discord_sent,
            "email_sent": h.email_sent,
            "user_acknowledged": h.user_acknowledged
        }
        for h in history
    ]

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Acknowledge an alert notification."""
    # Find the most recent alert history for this alert
    history = db.query(AlertHistory).join(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id,
        AlertHistory.user_acknowledged == False
    ).order_by(AlertHistory.triggered_at.desc()).first()
    
    if history:
        history.user_acknowledged = True
        history.acknowledged_at = datetime.now()
        db.commit()
        
        return {"message": "Alert acknowledged"}
    
    return {"message": "No pending alert to acknowledge"}

@router.get("/check/{symbol}")
async def check_alert_conditions(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Check current conditions for a symbol (for testing)."""
    # Get current technical data
    technical_data = await market_data_service.get_technical_analysis(symbol)
    
    if not technical_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data available for {symbol}"
        )
    
    # Get active alerts for this symbol
    alerts = db.query(Alert).filter(
        Alert.symbol == symbol.upper(),
        Alert.is_active == True
    ).all()
    
    results = []
    
    for alert in alerts:
        alert_result = {
            "alert_id": alert.id,
            "alert_name": alert.name,
            "conditions": []
        }
        
        for condition in alert.conditions:
            condition_met = _check_condition(condition, technical_data)
            
            alert_result["conditions"].append({
                "condition_type": condition.condition_type,
                "operator": condition.operator,
                "target_value": condition.target_value,
                "current_value": _get_current_value(condition.condition_type, technical_data),
                "is_met": condition_met
            })
        
        results.append(alert_result)
    
    return {
        "symbol": symbol,
        "current_data": technical_data,
        "alert_checks": results
    }

def _check_condition(condition: AlertCondition, technical_data: Dict) -> bool:
    """Check if a condition is met given current technical data."""
    current_value = _get_current_value(condition.condition_type, technical_data)
    
    if current_value is None:
        return False
    
    target = condition.target_value
    
    if condition.operator == "GT":
        return current_value > target
    elif condition.operator == "LT":
        return current_value < target
    elif condition.operator == "EQ":
        return abs(current_value - target) < 0.01  # Small tolerance for floats
    elif condition.operator == "GTE":
        return current_value >= target
    elif condition.operator == "LTE":
        return current_value <= target
    
    return False

def _get_current_value(condition_type: str, technical_data: Dict) -> Optional[float]:
    """Get current value for a condition type from technical data."""
    mapping = {
        "PRICE": "close",
        "ATR_DISTANCE": "atr_distance",
        "ATR_PERCENT": "atr_percent",
        "RSI": "rsi",
        "MACD": "macd",
        "ADX": "adx",
        "VOLUME": "volume"
    }
    
    field = mapping.get(condition_type)
    if field:
        return technical_data.get(field)
    
    return None 