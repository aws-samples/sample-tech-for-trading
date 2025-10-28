"""
lambda_function.py

Risk Manager Lambda Function
Provides real-time news and macroeconomic data using the yfinance library.
"""

import os
import json
import yfinance as yf
from datetime import datetime, timedelta

def get_product_news(ticker, top_n=5):
    """Retrieve latest news for specific ETF"""
    try:
        # Retrieve ETF news using yfinance
        stock = yf.Ticker(ticker)
        news = stock.news[:top_n]
        
        # Format news data
        formatted_news = []
        for item in news:
            # Extract data from content object
            content = item.get("content", item)
            
            title = content.get("title", "")
            summary = content.get("summary", "")
            
            # Process date
            pub_date = content.get("pubDate", "")
            publish_date = pub_date.split("T")[0] if "T" in pub_date else pub_date[:10] if len(pub_date) >= 10 else ""
            
            # Process link
            link = ""
            if "canonicalUrl" in content:
                link = content["canonicalUrl"].get("url", "")
            
            news_item = {
                "title": title,
                "summary": summary,
                "publish_date": publish_date,
                "link": link
            }
            formatted_news.append(news_item)
        
        return {
            "ticker": ticker,
            "news": formatted_news,
            "count": len(formatted_news)
        }
        
    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "news": []
        }

def get_market_data():
    """Retrieve major macroeconomic indicator data"""
    try:
        # Define major macroeconomic indicators (7 indicators)
        market_indicators = {
            # Interest rate indicators (3)
            "us_2y_treasury_yield": {"ticker": "^IRX", "description": "US 2-Year Treasury Yield (%)"},
            "us_10y_treasury_yield": {"ticker": "^TNX", "description": "US 10-Year Treasury Yield (%)"},
            "us_dollar_index": {"ticker": "DX-Y.NYB", "description": "US Dollar Strength Index"},
            
            # Volatility and commodities (3)
            "vix_volatility_index": {"ticker": "^VIX", "description": "VIX Volatility Index (Fear Index)"},
            "crude_oil_price": {"ticker": "CL=F", "description": "WTI Crude Oil Futures Price (USD/barrel)"},
            "gold_price": {"ticker": "GC=F", "description": "Gold Futures Price (USD/ounce)"},
            
            # Stock index (1)
            "sp500_index": {"ticker": "^GSPC", "description": "S&P 500 Index"}
        }
        
        market_data = {}
        
        # Retrieve data for each indicator
        for key, info in market_indicators.items():
            ticker_symbol = info["ticker"]
            
            try:
                ticker = yf.Ticker(ticker_symbol)
                info_data = ticker.info
                
                # Extract price information
                market_price = (info_data.get('regularMarketPrice') or 
                              info_data.get('regularMarketPreviousClose') or 
                              info_data.get('previousClose') or 0.0)
                
                market_data[key] = {
                    "description": info["description"],
                    "value": round(float(market_price), 2),
                    "ticker": ticker_symbol
                }
                
            except:
                market_data[key] = {
                    "description": info["description"],
                    "value": 0.0,
                    "ticker": ticker_symbol
                }
        
        return market_data
        
    except Exception as e:
        return {"error": f"Error fetching market data: {str(e)}"}

def get_geopolitical_indicators():
    """Retrieve geopolitical risk indicator data"""
    try:
        # Define geopolitical risk indicators (5 major regional ETFs)
        geopolitical_indicators = {
            "china_market": {"ticker": "ASHR", "description": "China A-Shares ETF"},
            "emerging_markets": {"ticker": "EEM", "description": "Emerging Markets ETF"},
            "europe_market": {"ticker": "VGK", "description": "Europe ETF"},
            "japan_market": {"ticker": "EWJ", "description": "Japan ETF"},
            "korea_market": {"ticker": "EWY", "description": "South Korea ETF"}
        }
        
        geopolitical_data = {}
        
        # Retrieve data for each indicator
        for key, info in geopolitical_indicators.items():
            ticker_symbol = info["ticker"]
            
            try:
                ticker = yf.Ticker(ticker_symbol)
                info_data = ticker.info
                
                # Extract price information
                market_price = (info_data.get('regularMarketPrice') or 
                              info_data.get('regularMarketPreviousClose') or 
                              info_data.get('previousClose') or 0.0)
                
                geopolitical_data[key] = {
                    "description": info["description"],
                    "value": round(float(market_price), 2),
                    "ticker": ticker_symbol
                }
                
            except:
                geopolitical_data[key] = {
                    "description": info["description"],
                    "value": 0.0,
                    "ticker": ticker_symbol
                }
        
        return geopolitical_data
        
    except Exception as e:
        return {"error": f"Error fetching geopolitical data: {str(e)}"}

def lambda_handler(event, context):
    """AWS Lambda main handler function"""
    try:
        tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        function_name = tool_name.split('___')[-1] if '___' in tool_name else tool_name
        
        if function_name == 'get_product_news':
            ticker = event.get('ticker', "")
            if not ticker:
                output = {"error": "ticker parameter is required"}
            else:
                output = get_product_news(ticker)
                
        elif function_name == 'get_market_data':
            output = get_market_data()
            
        elif function_name == 'get_geopolitical_indicators':
            output = get_geopolitical_indicators()
                
        else:
            output = {"error": f"Invalid function: {function_name}"}
        
        return {
            'statusCode': 200, 
            'body': json.dumps(output, ensure_ascii=False)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)}, ensure_ascii=False)
        }