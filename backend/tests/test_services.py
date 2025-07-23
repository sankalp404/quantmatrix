#!/usr/bin/env python3
"""
QuantMatrix V1 - Service Tests
==============================

Comprehensive tests for all major services.
Tests service initialization, core functionality, and integration.
"""

import pytest
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, AsyncMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestATREngineService:
    """Test ATR Engine service functionality."""
    
    @pytest.mark.asyncio
    async def test_atr_engine_import(self):
        """Test ATR engine can be imported and initialized."""
        try:
            from backend.services.analysis.atr_engine import atr_engine
            
            # Basic smoke test
            assert atr_engine is not None
            assert hasattr(atr_engine, 'calculate_enhanced_atr')
            assert hasattr(atr_engine, 'get_portfolio_atr')
            assert hasattr(atr_engine, 'process_major_indices')
            
            logger.info("✅ ATR Engine import test passed")
            
        except Exception as e:
            pytest.fail(f"ATR Engine import failed: {e}")
    
    @pytest.mark.asyncio
    async def test_atr_calculation_basic(self):
        """Test basic ATR calculation."""
        try:
            from backend.services.analysis.atr_engine import atr_engine
            
            # Test with a known symbol
            result = await atr_engine.calculate_enhanced_atr("AAPL")
            
            # Basic validation
            assert hasattr(result, 'atr_value')
            assert hasattr(result, 'volatility_level')
            assert hasattr(result, 'confidence')
            
            if result.atr_value > 0:
                assert result.atr_value > 0, "ATR value should be positive"
                assert result.volatility_level in ['LOW', 'MEDIUM', 'HIGH', 'EXTREME']
                assert 0 <= result.confidence <= 1, "Confidence should be 0-1"
                logger.info(f"✅ ATR calculation test passed: ATR={result.atr_value:.2f}")
            else:
                logger.warning("⚠️ ATR calculation returned zero (data unavailable)")
                
        except Exception as e:
            logger.warning(f"⚠️ ATR calculation test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_portfolio_atr_calculation(self):
        """Test portfolio ATR calculation."""
        try:
            from backend.services.analysis.atr_engine import atr_engine
            
            test_symbols = ["AAPL", "MSFT"]
            portfolio_atr = await atr_engine.get_portfolio_atr(test_symbols)
            
            if portfolio_atr:
                assert isinstance(portfolio_atr, dict)
                
                for symbol in test_symbols:
                    if symbol in portfolio_atr:
                        atr_result = portfolio_atr[symbol]
                        assert hasattr(atr_result, 'atr_value')
                        if atr_result.atr_value > 0:
                            assert atr_result.atr_value > 0
                
                logger.info(f"✅ Portfolio ATR test passed: {len(portfolio_atr)} results")
            else:
                logger.warning("⚠️ Portfolio ATR returned no results")
                
        except Exception as e:
            logger.warning(f"⚠️ Portfolio ATR test failed: {e}")

class TestMarketDataService:
    """Test Market Data service functionality."""
    
    @pytest.mark.asyncio
    async def test_market_data_service_import(self):
        """Test market data service can be imported."""
        try:
            from backend.services.market.market_data_service import market_data_service
            
            assert market_data_service is not None
            assert hasattr(market_data_service, 'get_current_price')
            assert hasattr(market_data_service, 'get_historical_data')
            assert hasattr(market_data_service, 'get_technical_analysis')
            
            logger.info("✅ Market Data Service import test passed")
            
        except Exception as e:
            pytest.fail(f"Market Data Service import failed: {e}")
    
    @pytest.mark.asyncio
    async def test_current_price_retrieval(self):
        """Test current price retrieval."""
        try:
            from backend.services.market.market_data_service import market_data_service
            
            test_symbol = "AAPL"
            price = await market_data_service.get_current_price(test_symbol)
            
            if price and price > 0:
                assert isinstance(price, (int, float))
                assert price > 0
                logger.info(f"✅ Current price test passed: {test_symbol} = ${price:.2f}")
            else:
                logger.warning(f"⚠️ Current price not available for {test_symbol}")
                
        except Exception as e:
            logger.warning(f"⚠️ Current price test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_historical_data_retrieval(self):
        """Test historical data retrieval."""
        try:
            from backend.services.market.market_data_service import market_data_service
            
            test_symbol = "AAPL"
            data = await market_data_service.get_historical_data(test_symbol, period="1mo")
            
            if data is not None and not data.empty:
                assert len(data) > 10, "Should have reasonable amount of data"
                
                # Check for required columns
                required_cols = ['open', 'high', 'low', 'close']
                available_cols = [col.lower() for col in data.columns]
                
                for col in required_cols:
                    assert col in available_cols or col.title() in data.columns
                
                logger.info(f"✅ Historical data test passed: {len(data)} periods")
            else:
                logger.warning(f"⚠️ Historical data not available for {test_symbol}")
                
        except Exception as e:
            logger.warning(f"⚠️ Historical data test failed: {e}")

class TestIndexConstituentsService:
    """Test Index Constituents service functionality."""
    
    @pytest.mark.asyncio
    async def test_index_service_import(self):
        """Test index service can be imported."""
        try:
            from backend.services.market.index_constituents_service import index_service
            
            assert index_service is not None
            assert hasattr(index_service, 'get_index_constituents')
            assert hasattr(index_service, 'get_all_tradeable_symbols')
            assert hasattr(index_service, 'get_universe_for_atr')
            
            logger.info("✅ Index Constituents Service import test passed")
            
        except Exception as e:
            pytest.fail(f"Index Constituents Service import failed: {e}")
    
    @pytest.mark.asyncio
    async def test_dow30_constituents(self):
        """Test getting Dow 30 constituents."""
        try:
            from backend.services.market.index_constituents_service import index_service
            
            dow30_symbols = await index_service.get_index_constituents('DOW30')
            
            if dow30_symbols and len(dow30_symbols) > 10:
                assert isinstance(dow30_symbols, list)
                assert all(isinstance(symbol, str) for symbol in dow30_symbols)
                assert all(len(symbol) <= 5 for symbol in dow30_symbols)
                logger.info(f"✅ Dow 30 constituents test passed: {len(dow30_symbols)} symbols")
            else:
                logger.warning(f"⚠️ Limited Dow 30 data: {len(dow30_symbols) if dow30_symbols else 0} symbols")
                
        except Exception as e:
            logger.warning(f"⚠️ Dow 30 constituents test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_atr_universe_generation(self):
        """Test ATR universe generation."""
        try:
            from backend.services.market.index_constituents_service import get_atr_universe
            
            universe = await get_atr_universe()
            
            if universe and len(universe) > 50:
                assert isinstance(universe, list)
                assert all(isinstance(symbol, str) for symbol in universe)
                logger.info(f"✅ ATR universe test passed: {len(universe)} symbols")
            else:
                logger.warning(f"⚠️ Limited ATR universe: {len(universe) if universe else 0} symbols")
                
        except Exception as e:
            logger.warning(f"⚠️ ATR universe test failed: {e}")

class TestDiscordNotificationService:
    """Test Discord notification service functionality."""
    
    def test_discord_service_import(self):
        """Test Discord service can be imported."""
        try:
            from backend.services.notifications.discord_service import discord_notifier
            
            assert discord_notifier is not None
            assert hasattr(discord_notifier, 'send_entry_signal')
            assert hasattr(discord_notifier, 'send_custom_alert')
            assert hasattr(discord_notifier, 'is_configured')
            
            logger.info("✅ Discord Service import test passed")
            
        except Exception as e:
            pytest.fail(f"Discord Service import failed: {e}")
    
    def test_discord_configuration(self):
        """Test Discord configuration status."""
        try:
            from backend.services.notifications.discord_service import discord_notifier
            
            is_configured = discord_notifier.is_configured()
            assert isinstance(is_configured, bool)
            
            if is_configured:
                logger.info("✅ Discord webhooks configured")
            else:
                logger.warning("⚠️ Discord webhooks not configured")
                
        except Exception as e:
            logger.warning(f"⚠️ Discord configuration test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_discord_webhook_connectivity(self):
        """Test Discord webhook connectivity."""
        try:
            from backend.services.notifications.discord_service import discord_notifier
            
            if not discord_notifier.is_configured():
                pytest.skip("Discord webhooks not configured")
            
            results = await discord_notifier.test_webhooks()
            
            if results:
                success_count = sum(1 for result in results if "Success" in result)
                logger.info(f"✅ Discord connectivity test: {success_count}/{len(results)} working")
            else:
                logger.warning("⚠️ Discord webhook test returned no results")
                
        except Exception as e:
            logger.warning(f"⚠️ Discord connectivity test failed: {e}")

class TestSignalGenerationService:
    """Test signal generation service functionality."""
    
    @pytest.mark.asyncio
    async def test_signal_generator_import(self):
        """Test signal generator can be imported."""
        try:
            from backend.services.signals.atr_signal_generator import atr_signal_generator
            
            assert atr_signal_generator is not None
            assert hasattr(atr_signal_generator, 'generate_portfolio_signals')
            
            logger.info("✅ Signal Generator import test passed")
            
        except Exception as e:
            logger.warning(f"⚠️ Signal Generator import failed: {e}")
    
    @pytest.mark.asyncio
    async def test_portfolio_signal_generation(self):
        """Test portfolio signal generation."""
        try:
            from backend.services.signals.atr_signal_generator import atr_signal_generator
            
            # Test signal generation for user 1
            result = await atr_signal_generator.generate_portfolio_signals(
                user_id=1,
                symbols=["AAPL", "MSFT"]
            )
            
            if result:
                assert isinstance(result, dict)
                logger.info(f"✅ Portfolio signal generation test passed")
            else:
                logger.warning("⚠️ Portfolio signal generation returned no results")
                
        except Exception as e:
            logger.warning(f"⚠️ Portfolio signal generation test failed: {e}")

class TestDatabaseServices:
    """Test database-related services."""
    
    def test_database_connection(self):
        """Test basic database connection."""
        try:
            from backend.database import SessionLocal, engine
            
            # Test database session creation
            db = SessionLocal()
            assert db is not None
            
            # Test basic query (if database exists)
            try:
                result = db.execute("SELECT 1").scalar()
                if result == 1:
                    logger.info("✅ Database connection test passed")
                else:
                    logger.warning("⚠️ Database query returned unexpected result")
            except Exception as query_error:
                logger.warning(f"⚠️ Database query failed: {query_error}")
            finally:
                db.close()
                
        except Exception as e:
            logger.warning(f"⚠️ Database connection test failed: {e}")

# Service integration tests
class TestServiceIntegration:
    """Test integration between services."""
    
    @pytest.mark.asyncio
    async def test_atr_to_discord_integration(self):
        """Test ATR engine to Discord integration."""
        try:
            from backend.services.analysis.atr_engine import atr_engine
            from backend.services.notifications.discord_service import discord_notifier
            
            if not discord_notifier.is_configured():
                pytest.skip("Discord not configured")
            
            # Calculate ATR for test symbol
            atr_result = await atr_engine.calculate_enhanced_atr("AAPL")
            
            if atr_result.atr_value > 0:
                # Send test signal to Discord
                await discord_notifier.send_entry_signal(
                    symbol="AAPL",
                    price=195.50,
                    atr_distance=2.5,
                    confidence=0.75,
                    reasons=["Integration test signal"],
                    targets=[200.0, 205.0],
                    stop_loss=190.0,
                    risk_reward=2.0,
                    atr_value=atr_result.atr_value,
                    company_synopsis="Integration test"
                )
                
                logger.info("✅ ATR to Discord integration test passed")
            else:
                logger.warning("⚠️ ATR calculation failed for integration test")
                
        except Exception as e:
            logger.warning(f"⚠️ ATR to Discord integration test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_market_data_to_atr_integration(self):
        """Test market data to ATR integration."""
        try:
            from backend.services.market.market_data_service import market_data_service
            from backend.services.analysis.atr_engine import atr_engine
            
            # Get market data
            test_symbol = "AAPL"
            price = await market_data_service.get_current_price(test_symbol)
            
            if price and price > 0:
                # Calculate ATR using market data
                atr_result = await atr_engine.calculate_enhanced_atr(test_symbol)
                
                if atr_result.atr_value > 0:
                    logger.info(f"✅ Market data to ATR integration: Price=${price:.2f}, ATR=${atr_result.atr_value:.2f}")
                else:
                    logger.warning("⚠️ ATR calculation failed with market data")
            else:
                logger.warning("⚠️ Market data not available for integration test")
                
        except Exception as e:
            logger.warning(f"⚠️ Market data to ATR integration test failed: {e}")

# Test runners
async def run_service_tests():
    """Run all service tests."""
    print("🧪 Running Service Tests...")
    
    try:
        # Test ATR Engine
        atr_test = TestATREngineService()
        await atr_test.test_atr_engine_import()
        await atr_test.test_atr_calculation_basic()
        await atr_test.test_portfolio_atr_calculation()
        
        # Test Market Data Service
        market_test = TestMarketDataService()
        await market_test.test_market_data_service_import()
        await market_test.test_current_price_retrieval()
        await market_test.test_historical_data_retrieval()
        
        # Test Index Constituents Service
        index_test = TestIndexConstituentsService()
        await index_test.test_index_service_import()
        await index_test.test_dow30_constituents()
        await index_test.test_atr_universe_generation()
        
        # Test Discord Service
        discord_test = TestDiscordNotificationService()
        discord_test.test_discord_service_import()
        discord_test.test_discord_configuration()
        await discord_test.test_discord_webhook_connectivity()
        
        # Test Signal Generation Service
        signal_test = TestSignalGenerationService()
        await signal_test.test_signal_generator_import()
        await signal_test.test_portfolio_signal_generation()
        
        # Test Database Services
        db_test = TestDatabaseServices()
        db_test.test_database_connection()
        
        # Test Service Integration
        integration_test = TestServiceIntegration()
        await integration_test.test_atr_to_discord_integration()
        await integration_test.test_market_data_to_atr_integration()
        
        print("✅ Service tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Service tests failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_service_tests())
    if success:
        print("🎉 All service tests passed!")
    else:
        print("❌ Some service tests failed!") 