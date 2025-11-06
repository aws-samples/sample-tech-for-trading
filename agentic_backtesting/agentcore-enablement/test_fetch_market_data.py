#!/usr/bin/env python3
"""
Test script for fetch_market_data_via_gateway function with AMZN
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fetch_market_data():
    """Test the fetch_market_data_via_gateway function"""
    print("🧪 Testing fetch_market_data_via_gateway with AMZN")
    print("=" * 50)
    
    try:
        # Import the function from agent.py
        from agent import fetch_market_data_via_gateway
        
        print("✅ Successfully imported fetch_market_data_via_gateway")
        
        # Test with AMZN symbol
        print("\n📊 Fetching AMZN market data...")
        result = fetch_market_data_via_gateway(symbol="AMZN")
        
        if result:
            print("✅ Market data fetch successful!")
            print(f"   Symbol: {result.get('symbol', 'N/A')}")
            print(f"   Data Points: {result.get('data_points', 'N/A')}")
            print(f"   Period: {result.get('period_start', 'N/A')} to {result.get('period_end', 'N/A')}")
            print(f"   Source: {result.get('source', 'N/A')}")
            
            # Show price data
            price_data = result.get('price_data', {})
            if price_data:
                print(f"   Initial Price: ${price_data.get('initial_price', 0):.2f}")
                print(f"   Final Price: ${price_data.get('final_price', 0):.2f}")
                print(f"   Min Price: ${price_data.get('min_price', 0):.2f}")
                print(f"   Max Price: ${price_data.get('max_price', 0):.2f}")
            
            # Show statistics
            stats = result.get('statistics', {})
            if stats:
                print(f"   Total Return: {stats.get('total_return_pct', 0):.2f}%")
                print(f"   Avg Daily Volume: {stats.get('avg_daily_volume', 0):,}")
            
            # Show technical indicators
            indicators = result.get('technical_indicators', {})
            if indicators:
                sma_20 = indicators.get('current_sma_20')
                sma_50 = indicators.get('current_sma_50')
                if sma_20:
                    print(f"   Current SMA 20: ${sma_20:.2f}")
                if sma_50:
                    print(f"   Current SMA 50: ${sma_50:.2f}")
            
            # Indicate if this is real or fallback data
            if result.get('source') == 'fallback_data':
                print("\n⚠️ Note: This is fallback data (gateway connection failed)")
            elif result.get('source') == 'agentcore_gateway':
                print("\n🌐 Note: This is real data from AgentCore Gateway")
                
        else:
            print("❌ Market data fetch failed - no data returned")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure agent.py is in the same directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function"""
    print("🚀 Market Data Fetch Test")
    print("=" * 40)
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✅ .env file found")
    else:
        print("⚠️ .env file not found - using system environment variables")
    
    # Run the test
    test_fetch_market_data()
    
    print("\n🏁 Test completed!")
    print("=" * 40)

if __name__ == "__main__":
    main()