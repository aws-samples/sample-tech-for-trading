import pandas as pd
import numpy as np
import json
import boto3
from datetime import datetime, timedelta
import os
import re
from factors.base_factor import BaseFactor
import time

class AverageSentimentFactor(BaseFactor):
    """
    Average Sentiment factor implementation
    Measures the average sentiment of news and social media about a company
    using Amazon Bedrock's Nova pro model to analyze sentiment on a -1 to 1 scale.
    """
    
    def __init__(self, window=14, s3_bucket="stock-news-data-u9gs99r4"):
        """
        Initialize the Average Sentiment factor
        
        Parameters:
        - window: Number of days to average sentiment (default: 14 days)
        - s3_bucket: S3 bucket name containing market news data
        """
        self.window = window
        self.s3_bucket = s3_bucket
        super().__init__(
            name=f"AVGSENT{window}",
            factor_type="Sentiment",
            description=f"Average Sentiment over {window} days. Measures the average sentiment of news and social media about a company using Amazon Bedrock."
        )
    
    def _get_sentiment_from_bedrock(self, text):
        """
        Get sentiment score from Amazon Bedrock Nova pro model
        
        Parameters:
        - text: Text to analyze for sentiment
        
        Returns:
        - Sentiment score between -1 and 1
        """
        try:
            # Initialize Bedrock client with profile
            session = boto3.Session()
            bedrock_runtime = session.client(
                service_name='bedrock-runtime',
                region_name='us-east-1'  # Adjust region as needed
            )
            
            # Prepare prompt for sentiment analysis
            prompt = f"""
            Analyze the sentiment of the following text about a company's stock and financial performance.
            Rate the sentiment on a scale from -1 to 1, where:
            - -1 represents extremely negative sentiment
            - 0 represents neutral sentiment
            - 1 represents extremely positive sentiment
            
            Only respond with a single number between -1 and 1, with up to two decimal places.
            
            Text to analyze:
            {text}
            """
            
            # Call Amazon Nova pro model through Bedrock using converse API
            messages = [
                {"role": "user", "content": [{"text": prompt}]},
            ]
            
            response = bedrock_runtime.converse(
                modelId="us.amazon.nova-pro-v1:0",
                messages=messages
            )

            # sleep for one second because of ai quota
            time.sleep(1)


            # Parse response
            sentiment_text = response['output']['message']['content'][0]['text'].strip()

            # Convert to float and ensure it's in range [-1, 1]
            match = re.search(r'(-?\d+\.\d+)', sentiment_text)
            if match:
                sentiment_score = float(match.group(1))
                return max(min(sentiment_score, 1.0), -1.0)

            sentiment_score = float(sentiment_text)
            sentiment_score = max(min(sentiment_score, 1.0), -1.0)

            return sentiment_score
            
        except Exception as e:
            print(f"Error getting sentiment from Bedrock: {str(e)}")
            # Return neutral sentiment in case of error
            return 0.0
    
    def _get_news_from_s3(self, ticker, date):
        """
        Get market news data from S3 for a specific ticker and date
        
        Parameters:
        - ticker: Stock ticker symbol
        - date: Date string in format YYYY-MM-DD
        
        Returns:
        - Market news data as dictionary, or None if not found
        """
        try:
            # Use the factor profile for S3 access
            session = boto3.Session()
            s3_client = session.client('s3')
            s3_key = f"{ticker}/{date}/market_news.json"
            
            response = s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=s3_key
            )
            
            news_data = json.loads(response['Body'].read().decode('utf-8'))
            # news_data = response['Body'].read().decode('utf-8')
            return news_data
        except Exception as e:
            print(f"Error retrieving news for {ticker} on {date}: {str(e)}")
            return None
    
    def calculate(self, price_data):
        """
        Calculate Average Sentiment from S3 market news data using Amazon Bedrock
        
        Parameters:
        - price_data: Dictionary of DataFrames with price data (key=ticker, value=DataFrame)
        
        Returns:
        - DataFrame with Average Sentiment values (index=dates, columns=tickers)
        """
        # Get all unique dates from price data
        all_dates = set()
        for ticker, df in price_data.items():
            all_dates.update(df.index)
        
        all_dates = sorted(list(all_dates))
        sentiment_df = pd.DataFrame(index=all_dates)
        
        # Calculate daily sentiment for each stock
        daily_sentiment = {}
        
        for ticker in price_data.keys():
            ticker_sentiment = {}
            
            # Process each date for this ticker
            for date_obj in all_dates:
                date_str = date_obj.strftime('%Y-%m-%d')
                
                # Get news data from S3
                news_data = self._get_news_from_s3(ticker, date_str)
                # sentiment_score = self._get_sentiment_from_bedrock(news_data)
                # ticker_sentiment[date_obj] = sentiment_score


                if news_data and 'answer' in news_data:
                    # Extract the answer text
                    answer_text = news_data['answer']

                    # Get sentiment score from Bedrock
                    sentiment_score = self._get_sentiment_from_bedrock(answer_text)

                    # Store sentiment score
                    ticker_sentiment[date_obj] = sentiment_score
                else:
                    # No news data available, use neutral sentiment
                    ticker_sentiment[date_obj] = 0.0
            
            # Convert to Series
            daily_sentiment[ticker] = pd.Series(ticker_sentiment)
        
        # Calculate rolling average sentiment for each stock
        for ticker, sentiment_series in daily_sentiment.items():
            # Calculate rolling average
            rolling_sentiment = sentiment_series.rolling(window=self.window, min_periods=1).mean()
            
            # Add to DataFrame
            sentiment_df[ticker] = rolling_sentiment
        
        return sentiment_df
        
    def backfill_missing_dates(self, sentiment_df):
        """
        Backfill missing dates with the most recent available sentiment
        
        Parameters:
        - sentiment_df: DataFrame with sentiment values
        
        Returns:
        - DataFrame with backfilled sentiment values
        """
        return sentiment_df.fillna(method='ffill')


class NewsSentimentFactor(BaseFactor):
    """
    News Sentiment factor implementation
    Analyzes the sentiment of recent news articles about a company
    using Amazon Bedrock's Nova pro model.
    """
    
    def __init__(self, s3_bucket="stock-news-data-u9gs99r4"):
        """
        Initialize the News Sentiment factor
        
        Parameters:
        - s3_bucket: S3 bucket name containing market news data
        """
        self.s3_bucket = s3_bucket
        super().__init__(
            name="NEWSENT",
            factor_type="Sentiment",
            description="Sentiment of recent news articles about a company using Amazon Bedrock."
        )
    
    def _get_sentiment_from_bedrock(self, text):
        """
        Get sentiment score from Amazon Bedrock Nova pro model
        
        Parameters:
        - text: Text to analyze for sentiment
        
        Returns:
        - Sentiment score between -1 and 1
        """
        try:
            # Initialize Bedrock client with profile
            session = boto3.Session()
            bedrock_runtime = session.client(
                service_name='bedrock-runtime',
                region_name='us-east-1'  # Adjust region as needed
            )
            
            # Prepare prompt for sentiment analysis
            prompt = f"""
            Analyze the sentiment of the following text about a company's stock and financial performance.
            Rate the sentiment on a scale from -1 to 1, where:
            - -1 represents extremely negative sentiment
            - 0 represents neutral sentiment
            - 1 represents extremely positive sentiment
            
            Only respond with a single number between -1 and 1, with up to two decimal places. No need explanation.
            
            Text to analyze:
            {text}
            """
            
            # Call Amazon Nova pro model through Bedrock using converse API
            messages = [
                {"role": "user", "content": [{"text": prompt}]},
            ]
            
            response = bedrock_runtime.converse(
                modelId="us.amazon.nova-pro-v1:0",
                messages=messages
            )

            # sleep for one second because of ai quota
            time.sleep(1)
            
            # Parse response
            sentiment_text = response['output']['message']['content'][0]['text'].strip()
            
            # Convert to float and ensure it's in range [-1, 1]
            match = re.search(r'(-?\d+\.\d+)', sentiment_text)
            if match:
                sentiment_score =  float(match.group(1))
                return max(min(sentiment_score, 1.0), -1.0)

            sentiment_score = float(sentiment_text)
            sentiment_score = max(min(sentiment_score, 1.0), -1.0)
            
            return sentiment_score
            
        except Exception as e:
            print(f"Error getting sentiment from Bedrock: {str(e)}")
            # Return neutral sentiment in case of error
            return 0.0
    
    def _get_news_from_s3(self, ticker, date):
        """
        Get market news data from S3 for a specific ticker and date
        
        Parameters:
        - ticker: Stock ticker symbol
        - date: Date string in format YYYY-MM-DD
        
        Returns:
        - Market news data as dictionary, or None if not found
        """
        try:
            # Use the factor profile for S3 access
            session = boto3.Session()
            s3_client = session.client('s3')
            s3_key = f"{ticker}/{date}/market_news.json"
            
            response = s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=s3_key
            )
            
            news_data = json.loads(response['Body'].read().decode('utf-8'))
            return news_data
        except Exception as e:
            print(f"Error retrieving news for {ticker} on {date}: {str(e)}")
            return None
    
    def calculate(self, price_data):
        """
        Calculate News Sentiment from S3 market news data using Amazon Bedrock
        
        Parameters:
        - price_data: Dictionary of DataFrames with price data (key=ticker, value=DataFrame)
        
        Returns:
        - DataFrame with News Sentiment values (index=dates, columns=tickers)
        """
        # Get all unique dates from price data
        all_dates = set()
        for ticker, df in price_data.items():
            all_dates.update(df.index)
        
        all_dates = sorted(list(all_dates))
        sentiment_df = pd.DataFrame(index=all_dates)
        
        # Calculate daily sentiment for each stock
        for ticker in price_data.keys():
            ticker_sentiment = {}
            
            # Process each date for this ticker
            for date_obj in all_dates:
                date_str = date_obj.strftime('%Y-%m-%d')
                
                # Get news data from S3
                news_data = self._get_news_from_s3(ticker, date_str)
                
                if news_data and 'answer' in news_data:
                    # Extract the answer text
                    answer_text = news_data['answer']
                    
                    # Get sentiment score from Bedrock
                    sentiment_score = self._get_sentiment_from_bedrock(answer_text)
                    
                    # Store sentiment score
                    ticker_sentiment[date_obj] = sentiment_score
                else:
                    # No news data available, use neutral sentiment
                    ticker_sentiment[date_obj] = 0.0
            
            # Add to DataFrame
            sentiment_df[ticker] = pd.Series(ticker_sentiment)
        
        return sentiment_df
