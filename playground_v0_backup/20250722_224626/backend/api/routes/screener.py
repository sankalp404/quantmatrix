from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import asyncio

from backend.models import get_db
from backend.services.market_data import market_data_service
from backend.core.strategies.atr_matrix import atr_matrix_strategy
from backend.config import settings

router = APIRouter()

# Comprehensive stock universes with fund membership tracking
SP500_STOCKS = [
    # Technology
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "NFLX", "CRM",
    "ADBE", "PYPL", "INTC", "CSCO", "ORCL", "IBM", "QCOM", "TXN", "AVGO", "MU",
    "AMD", "NOW", "INTU", "AMAT", "LRCX", "ADI", "MRVL", "KLAC", "CDNS", "SNPS",
    "FTNT", "TEAM", "DDOG", "CRWD", "ZM", "DOCU", "OKTA", "SPLK", "WDAY", "VEEV",
    "ZS", "ESTC", "MDB", "NET", "SNOW", "PLTR", "RBLX", "U", "TWLO", "SHOP",
    
    # Healthcare
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY", "AMGN",
    "LLY", "MDT", "GILD", "CVS", "ANTM", "CI", "HUM", "CNC", "MOH", "WLP",
    "BIIB", "REGN", "VRTX", "ILMN", "IQV", "A", "BAX", "BDX", "BSX", "SYK",
    "ZBH", "EW", "HOLX", "ISRG", "VAR", "TECH", "PKI", "GEHC", "SOLV", "VTRS",
    
    # Financial Services  
    "JPM", "BAC", "WFC", "GS", "MS", "C", "USB", "PNC", "TFC", "COF",
    "BK", "STT", "NTRS", "RF", "CFG", "HBAN", "FITB", "ZION", "CMA", "MTB",
    "KEY", "WBS", "PBCT", "SNV", "SIVB", "SBNY", "FCNCA", "WAL", "EWBC", "PACW",
    "AXP", "V", "MA", "SPGI", "MCO", "BLK", "SCHW", "CME", "ICE", "NDAQ",
    
    # Consumer Discretionary
    "AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TJX", "LOW", "BKNG", "TGT",
    "GM", "F", "RIVN", "LCID", "UBER", "LYFT", "DASH", "ABNB", "ETSY", "W",
    "CHWY", "CHEWY", "PETS", "WOOF", "RH", "WSM", "BBY", "COST", "WMT", "DG",
    
    # Communication Services
    "GOOGL", "GOOG", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR",
    "DISH", "SIRI", "TWTR", "SNAP", "PINS", "MTCH", "IAC", "MSGS", "CABO", "LBRDK",
    
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "PSX", "VLO", "MPC", "OXY", "KMI",
    "PXD", "BKR", "HAL", "DVN", "FANG", "APA", "EQT", "CNX", "AR", "SM",
    "HP", "MRO", "OVV", "CLR", "WMB", "EPD", "ET", "MPLX", "PAA", "ENLC",
    
    # Industrials
    "BA", "CAT", "GE", "MMM", "HON", "UPS", "LMT", "RTX", "UNP", "FDX",
    "GD", "NOC", "LHX", "TDG", "CARR", "OTIS", "ITW", "EMR", "ETN", "PCAR",
    "CMI", "DE", "IR", "ROK", "DOV", "XYL", "FTV", "PH", "AME", "ROP",
    
    # Consumer Staples
    "PG", "KO", "PEP", "WMT", "COST", "MDLZ", "KHC", "GIS", "K", "HSY",
    "CPB", "CAG", "SJM", "HRL", "TSN", "TYSON", "ADM", "BG", "CF", "MOS",
    
    # Materials
    "LIN", "APD", "ECL", "FCX", "NEM", "FMC", "VMC", "MLM", "PKG", "BALL",
    "AVY", "CCK", "SEE", "IP", "WRK", "NUE", "STLD", "RS", "CMC", "CLF",
    
    # Real Estate
    "AMT", "PLD", "CCI", "EQIX", "DLR", "WELL", "EXR", "AVB", "EQR", "ESS",
    "UDR", "CPT", "MAA", "AIV", "SLG", "VNO", "BXP", "KIM", "REG", "FRT",
    
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ES",
    "ETR", "FE", "EVRG", "CNP", "NI", "LNT", "WTRG", "AWK", "CWT", "SJW"
]

NASDAQ_STOCKS = [
    # NASDAQ 100 core holdings
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AVGO", "ASML",
    "COST", "NFLX", "ADBE", "PEP", "TMUS", "CSCO", "CMCSA", "TXN", "QCOM", "HON",
    "INTU", "AMGN", "SBUX", "ISRG", "BKNG", "MDLZ", "GILD", "ADP", "VRTX", "ADI",
    "REGN", "LRCX", "FISV", "ATVI", "CSX", "PYPL", "CHTR", "MU", "KLAC", "ORLY",
    "MELI", "MNST", "FTNT", "DXCM", "NXPI", "KDP", "CTAS", "WDAY", "MRNA", "PCAR",
    "CDNS", "SNPS", "IDXX", "FAST", "CRWD", "BIIB", "LCID", "RIVN", "ZM", "DOCU",
    
    # Additional NASDAQ growth stocks
    "ROKU", "HOOD", "COIN", "SHOP", "SQ", "PLTR", "SNOW", "DDOG", "NET", "OKTA",
    "TWLO", "ESTC", "MDB", "ZS", "CFLT", "GTLB", "PATH", "TEAM", "ATLASSIAN", "NOW",
    "VEEV", "CRM", "ORCL", "ADSK", "ANSS", "CTSH", "PAYX", "VRSK", "MSCI", "VRSN",
    "SPLK", "PANW", "CYBR", "FEYE", "TENB", "RPD", "QLYS", "SAIL", "S", "DBX",
    
    # Biotech & Healthcare
    "BMRN", "EXAS", "TECH", "ALGN", "ILMN", "INCY", "VTRS", "TEVA", "JAZZ", "HALO",
    "SRPT", "RARE", "FOLD", "IMMU", "BGNE", "WVE", "IONS", "IOVA", "ACAD", "HZNP",
    
    # Consumer & Retail
    "PTON", "CHWY", "ETSY", "W", "OSTK", "CVNA", "CARG", "VIPS", "JD", "BABA",
    "PDD", "MELI", "GLOB", "TRIP", "EXPE", "PCLN", "GRUB", "UBER", "LYFT", "DASH"
]

RUSSELL_2000_STOCKS = [
    # Representative Russell 2000 small-cap stocks
    "IWM", "VTWO", "SCHA", "IJR", "SLY", "VTI", "ITOT", "SPTM", "SCHB", "VXF",
    "SPMD", "SPSM", "VB", "VTEB", "VTHR", "VTV", "VOE", "VBR", "VBK", "VUG",
    
    # Small-cap growth stocks
    "UPST", "AFRM", "SOFI", "OPEN", "ROOT", "LMND", "MTTR", "PATH", "FROG", "BIRD",
    "SPCE", "RKLB", "JOBY", "LILM", "EH", "NKLA", "FSR", "GOEV", "WKHS", "RIDE",
    "BLNK", "CHPT", "EVGO", "WBX", "QS", "STEM", "SUNW", "NOVA", "ARRY", "ENPH",
    
    # Small-cap value stocks  
    "AMC", "GME", "BBBY", "EXPR", "MVIS", "SNDL", "NAKD", "CLOV", "WISH", "SPRT",
    "IRNT", "OPAD", "DWAC", "PHUN", "MARK", "CARV", "PROG", "ATER", "BBIG", "CEI",
    
    # Emerging sectors
    "TLRY", "CGC", "ACB", "CRON", "HEXO", "OGI", "APHA", "SNDL", "ZYNE", "GRWG",
    "SMG", "HYFM", "IIPR", "CCHWF", "TCNNF", "GTBIF", "CURLF", "CRLBF", "AYRWF", "GNLN",
    
    # Technology small-caps
    "RAVN", "SIFY", "VNET", "WIX", "MNDY", "FVRR", "WORK", "ZI", "BILL", "APPS",
    "NCNO", "ASAN", "PD", "FIVN", "ESTC", "DOMO", "AI", "C3AI", "BBAI", "SOUN",
    
    # Healthcare & Biotech small-caps
    "NVAX", "NOVN", "GTHX", "ADMA", "ARDS", "ARQT", "AVIR", "CERS", "CVAC", "DYAI",
    "EYEN", "FATB", "GLYC", "GRTS", "HGEN", "HTBX", "IBRX", "ICCC", "IMAB", "KPTI"
]

# Fund membership mapping
FUND_MEMBERSHIP = {
    # S&P 500 mapping
    **{symbol: "S&P 500" for symbol in SP500_STOCKS},
    # NASDAQ mapping  
    **{symbol: "NASDAQ" for symbol in NASDAQ_STOCKS},
    # Russell 2000 mapping
    **{symbol: "Russell 2000" for symbol in RUSSELL_2000_STOCKS}
}

# Market cap categories
MARKET_CAP_CATEGORIES = {
    "MEGA_CAP": 200_000_000_000,  # $200B+
    "LARGE_CAP": 10_000_000_000,  # $10B-$200B  
    "MID_CAP": 2_000_000_000,     # $2B-$10B
    "SMALL_CAP": 300_000_000,     # $300M-$2B
    "MICRO_CAP": 50_000_000,      # $50M-$300M
    "NANO_CAP": 0                 # <$50M
}

# Combined universe for comprehensive scanning
ALL_STOCKS = list(set(SP500_STOCKS + NASDAQ_STOCKS + RUSSELL_2000_STOCKS))

# Legacy popular stocks list (kept for backwards compatibility)
POPULAR_STOCKS = SP500_STOCKS[:60]  # Top 60 S&P 500 stocks

# Pydantic models
class ScreenerCriteria(BaseModel):
    min_atr_distance: Optional[float] = None
    max_atr_distance: Optional[float] = None
    min_atr_percent: Optional[float] = None
    max_atr_percent: Optional[float] = None
    require_ma_alignment: Optional[bool] = None
    min_price_position_20d: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_volume: Optional[int] = None
    sectors: Optional[List[str]] = None
    exclude_symbols: Optional[List[str]] = None
    custom_symbols: Optional[List[str]] = None

class ScreenerResult(BaseModel):
    symbol: str
    name: str
    current_price: float
    sector: Optional[str]
    industry: Optional[str]
    
    # ATR Matrix metrics
    atr_distance: Optional[float]
    atr_percent: Optional[float] 
    atr: Optional[float]  # Add missing ATR value
    ma_aligned: Optional[bool]
    ma_alignment: Optional[bool]  # Alternative key for compatibility
    price_position_20d: Optional[float]
    
    # Technical indicators
    rsi: Optional[float]
    macd: Optional[float]
    adx: Optional[float]
    
    # Strategy assessment
    recommendation: str
    confidence: float
    overall_score: float
    
    # Additional metrics
    volume: Optional[float]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    
    # Signals
    entry_signal: Optional[Dict[str, Any]]
    scale_out_signals: List[Dict[str, Any]]
    risk_alerts: List[Dict[str, Any]]

class ScreenerResponse(BaseModel):
    total_scanned: int
    results_count: int
    scan_time: float
    criteria: ScreenerCriteria
    results: List[ScreenerResult]
    top_picks: List[ScreenerResult]

class ATRMatrixScanRequest(BaseModel):
    symbols: Optional[List[str]] = None
    max_distance: float = 4.0
    require_ma_alignment: bool = False
    min_atr_percent: float = 2.0
    min_confidence: float = 0.6

@router.post("/run", response_model=ScreenerResponse)
async def run_screener(
    criteria: ScreenerCriteria,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run a custom screener with specified criteria."""
    start_time = datetime.now()
    
    # Determine symbols to scan - now uses comprehensive universe
    symbols_to_scan = criteria.custom_symbols or ALL_STOCKS
    
    # Apply symbol filters
    if criteria.exclude_symbols:
        symbols_to_scan = [s for s in symbols_to_scan if s not in criteria.exclude_symbols]
    
    # Limit to max scanner capacity
    symbols_to_scan = symbols_to_scan[:settings.MAX_SCANNER_TICKERS]
    
    # Run screening
    results = await _scan_symbols(symbols_to_scan, criteria)
    
    # Calculate scan time
    scan_time = (datetime.now() - start_time).total_seconds()
    
    # Sort by overall score
    results.sort(key=lambda x: x.overall_score, reverse=True)
    
    # Get top picks (top 10)
    top_picks = results[:10]
    
    return ScreenerResponse(
        total_scanned=len(symbols_to_scan),
        results_count=len(results),
        scan_time=scan_time,
        criteria=criteria,
        results=results,
        top_picks=top_picks
    )

@router.post("/atr-matrix", response_model=ScreenerResponse)
async def atr_matrix_scan(
    request: ATRMatrixScanRequest,
    db: Session = Depends(get_db)
):
    """Run ATR Matrix specific scan for entry opportunities."""
    start_time = datetime.now()
    
    # Use provided symbols or default comprehensive list
    symbols_to_scan = request.symbols or ALL_STOCKS
    symbols_to_scan = symbols_to_scan[:settings.MAX_SCANNER_TICKERS]
    
    # Create criteria for ATR Matrix scan
    criteria = ScreenerCriteria(
        max_atr_distance=request.max_distance,
        min_atr_percent=request.min_atr_percent,
        require_ma_alignment=request.require_ma_alignment,
        min_price_position_20d=50.0  # Above 50% in 20-day range
    )
    
    # Run screening
    results = await _scan_symbols(symbols_to_scan, criteria)
    
    # Filter by confidence
    results = [r for r in results if r.confidence >= request.min_confidence]
    
    # Filter for entry signals only
    entry_opportunities = [r for r in results if r.entry_signal]
    
    # Sort by ATR distance (closer to SMA50 is better for entries)
    entry_opportunities.sort(key=lambda x: x.atr_distance or 999)
    
    scan_time = (datetime.now() - start_time).total_seconds()
    
    return ScreenerResponse(
        total_scanned=len(symbols_to_scan),
        results_count=len(entry_opportunities),
        scan_time=scan_time,
        criteria=criteria,
        results=entry_opportunities,
        top_picks=entry_opportunities[:5]  # Top 5 ATR Matrix picks
    )

def get_market_cap_category(market_cap: float) -> str:
    """Categorize market cap into standard buckets."""
    if market_cap >= MARKET_CAP_CATEGORIES["MEGA_CAP"]:
        return "Mega Cap ($200B+)"
    elif market_cap >= MARKET_CAP_CATEGORIES["LARGE_CAP"]:
        return "Large Cap ($10B-$200B)"
    elif market_cap >= MARKET_CAP_CATEGORIES["MID_CAP"]:
        return "Mid Cap ($2B-$10B)"
    elif market_cap >= MARKET_CAP_CATEGORIES["SMALL_CAP"]:
        return "Small Cap ($300M-$2B)"
    elif market_cap >= MARKET_CAP_CATEGORIES["MICRO_CAP"]:
        return "Micro Cap ($50M-$300M)"
    else:
        return "Nano Cap (<$50M)"

def get_fund_membership(symbol: str) -> str:
    """Get fund membership for a symbol."""
    memberships = []
    if symbol in SP500_STOCKS:
        memberships.append("S&P 500")
    if symbol in NASDAQ_STOCKS:
        memberships.append("NASDAQ")  
    if symbol in RUSSELL_2000_STOCKS:
        memberships.append("Russell 2000")
    
    if not memberships:
        return "Not in major indices"
    elif len(memberships) == 1:
        return memberships[0]
    else:
        return " & ".join(memberships)

@router.get("/stock-universe")
async def get_stock_universe():
    """Get comprehensive stock universe information."""
    return {
        "total_stocks": len(ALL_STOCKS),
        "breakdown": {
            "sp500": len(SP500_STOCKS),
            "nasdaq": len(NASDAQ_STOCKS), 
            "russell_2000": len(RUSSELL_2000_STOCKS),
            "unique_total": len(set(ALL_STOCKS))
        },
        "sample_stocks": {
            "sp500_sample": SP500_STOCKS[:10],
            "nasdaq_sample": NASDAQ_STOCKS[:10],
            "russell_2000_sample": RUSSELL_2000_STOCKS[:10]
        }
    }

@router.get("/popular-stocks")
async def get_popular_stocks():
    """Get list of popular stocks for screening (legacy endpoint)."""
    return {
        "symbols": POPULAR_STOCKS,
        "count": len(POPULAR_STOCKS),
        "note": "This is a subset of S&P 500. Use /stock-universe for full coverage.",
        "categories": {
            "sp500_top_60": POPULAR_STOCKS
        }
    }

@router.get("/preset-scans")
async def get_preset_scans():
    """Get predefined screening presets."""
    return {
        "atr_matrix_entry": {
            "name": "ATR Matrix Entry Setup",
            "description": "Stocks in ATR buy zone with aligned MAs",
            "criteria": {
                "max_atr_distance": 4.0,
                "require_ma_alignment": True,
                "min_atr_percent": 3.0,
                "min_price_position_20d": 60.0
            }
        },
        "breakout_candidates": {
            "name": "Breakout Candidates",
            "description": "Stocks near ATR scale-out levels",
            "criteria": {
                "min_atr_distance": 6.0,
                "max_atr_distance": 8.0,
                "min_atr_percent": 4.0
            }
        },
        "value_opportunities": {
            "name": "Value Opportunities",
            "description": "Quality stocks below SMA50",
            "criteria": {
                "max_atr_distance": 0.0,
                "require_ma_alignment": False,
                "min_atr_percent": 2.0
            }
        },
        "momentum_plays": {
            "name": "Momentum Plays",
            "description": "Strong uptrend with high volatility",
            "criteria": {
                "min_atr_distance": 8.0,
                "require_ma_alignment": True,
                "min_atr_percent": 5.0,
                "min_price_position_20d": 80.0
            }
        }
    }

async def _scan_symbols(symbols: List[str], criteria: ScreenerCriteria) -> List[ScreenerResult]:
    """Internal function to scan symbols with given criteria."""
    results = []
    
    # Process in batches to avoid overwhelming the API
    batch_size = 20
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[_analyze_symbol(symbol, criteria) for symbol in batch],
            return_exceptions=True
        )
        
        for result in batch_results:
            if isinstance(result, ScreenerResult):
                results.append(result)
            # Skip exceptions/errors
    
    return results

async def _analyze_symbol(symbol: str, criteria: ScreenerCriteria) -> Optional[ScreenerResult]:
    """Analyze a single symbol against screening criteria."""
    try:
        # Get technical analysis
        technical_data = await market_data_service.get_technical_analysis(symbol)
        if not technical_data:
            return None
        
        # Get stock info
        stock_info = await market_data_service.get_stock_info(symbol)
        
        # Run strategy analysis
        strategy_analysis = await atr_matrix_strategy.analyze(symbol, technical_data)
        
        # Apply filters
        if not _passes_criteria(technical_data, stock_info, criteria):
            return None
        
        # Extract signals
        entry_signal = None
        scale_out_signals = []
        risk_alerts = []
        
        for signal in strategy_analysis.signals:
            signal_data = {
                'type': signal.signal_type,
                'strength': signal.strength,
                'price': signal.price,
                'metadata': signal.metadata
            }
            
            if signal.signal_type == "ENTRY":
                entry_signal = signal_data
            elif signal.signal_type == "SCALE_OUT":
                scale_out_signals.append(signal_data)
            elif signal.signal_type == "EXIT":
                risk_alerts.append(signal_data)
        
        return ScreenerResult(
            symbol=symbol,
            name=stock_info.get('name', ''),
            current_price=technical_data.get('close', 0),
            sector=stock_info.get('sector'),
            industry=stock_info.get('industry'),
            
            # ATR Matrix metrics
            atr_distance=technical_data.get('atr_distance'),
            atr_percent=technical_data.get('atr_percent'),
            atr=technical_data.get('atr'), # Add missing atr field
            ma_aligned=technical_data.get('ma_aligned'),
            ma_alignment=technical_data.get('ma_alignment'), # Alternative key for compatibility
            price_position_20d=technical_data.get('price_position_20d'),
            
            # Technical indicators
            rsi=technical_data.get('rsi'),
            macd=technical_data.get('macd'),
            adx=technical_data.get('adx'),
            
            # Strategy assessment
            recommendation=strategy_analysis.recommendation,
            confidence=strategy_analysis.confidence,
            overall_score=strategy_analysis.overall_score,
            
            # Additional metrics
            volume=technical_data.get('volume'),
            market_cap=stock_info.get('market_cap'),
            pe_ratio=stock_info.get('pe_ratio'),
            
            # Signals
            entry_signal=entry_signal,
            scale_out_signals=scale_out_signals,
            risk_alerts=risk_alerts
        )
        
    except Exception as e:
        # Log error and skip this symbol
        print(f"Error analyzing {symbol}: {e}")
        return None

def _passes_criteria(technical_data: Dict, stock_info: Dict, criteria: ScreenerCriteria) -> bool:
    """Check if a symbol passes the screening criteria."""
    
    # ATR Distance filters
    atr_distance = technical_data.get('atr_distance')
    if atr_distance is not None:
        if criteria.min_atr_distance is not None and atr_distance < criteria.min_atr_distance:
            return False
        if criteria.max_atr_distance is not None and atr_distance > criteria.max_atr_distance:
            return False
    
    # ATR Percent filters
    atr_percent = technical_data.get('atr_percent')
    if atr_percent is not None:
        if criteria.min_atr_percent is not None and atr_percent < criteria.min_atr_percent:
            return False
        if criteria.max_atr_percent is not None and atr_percent > criteria.max_atr_percent:
            return False
    
    # MA Alignment filter
    if criteria.require_ma_alignment:
        ma_aligned = technical_data.get('ma_aligned', False)
        if not ma_aligned:
            return False
    
    # Price position in 20-day range
    price_position = technical_data.get('price_position_20d')
    if criteria.min_price_position_20d is not None and price_position is not None:
        if price_position < criteria.min_price_position_20d:
            return False
    
    # Price filters
    current_price = technical_data.get('close', 0)
    if criteria.min_price is not None and current_price < criteria.min_price:
        return False
    if criteria.max_price is not None and current_price > criteria.max_price:
        return False
    
    # Volume filter
    volume = technical_data.get('volume')
    if criteria.min_volume is not None and volume is not None:
        if volume < criteria.min_volume:
            return False
    
    # Sector filter
    if criteria.sectors:
        sector = stock_info.get('sector')
        if sector not in criteria.sectors:
            return False
    
    return True 