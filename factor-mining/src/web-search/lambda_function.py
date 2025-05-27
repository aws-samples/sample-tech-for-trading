import json
import os
import boto3
import urllib.request
import urllib.parse
import datetime
from datetime import datetime, timezone

def lambda_handler(event, context):
    # Get parameters from environment variables or event
    tickers = event.get('tickers', [os.environ.get('DEFAULT_TICKER', 'AAPL')])
    target_date = event.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    s3_bucket = os.environ.get('S3_BUCKET')
    
    if not s3_bucket:
        return {
            'statusCode': 500,
            'body': json.dumps('S3 bucket name not provided')
        }
    
    # Get Tavily API key from Secrets Manager
    tavily_api_key = get_secret(os.environ.get('TAVILY_API_KEY_NAME'))
    
    if not tavily_api_key:
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to retrieve Tavily API key')
        }
    
    results = {}
    
    # Process each ticker
    for ticker in tickers:
        # Search for stock news using Tavily API
        search_query = f"{ticker} stock news"
        news_data = search_web(search_query, tavily_api_key, days=1)  # Get only today's news
        
        if news_data:
            # Save news to S3
            s3_key = f"{ticker}/{target_date}/market_news.json"
            save_to_s3(s3_bucket, s3_key, news_data)
            results[ticker] = f"Successfully saved news data to S3"
        else:
            results[ticker] = f"No news found"
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def get_secret(secret_name):
    """Retrieve a secret from AWS Secrets Manager."""
    if not secret_name:
        return None
        
    try:
        session = boto3.session.Session()
        secrets_manager = session.client(service_name="secretsmanager")
        secret_value = secrets_manager.get_secret_value(SecretId=secret_name)
        return secret_value["SecretString"]
    except Exception as e:
        print(f"Error retrieving secret {secret_name}: {str(e)}")
        return None

def search_web(search_query, api_key, target_website="", topic="finance", days=1):
    """Search the web using Tavily API."""
    print(f"Executing Tavily AI search with query: {search_query}")

    base_url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {
        "api_key": api_key,
        "query": search_query,
        "search_depth": "advanced",
        "include_images": False,
        "include_answer": True,
        "include_raw_content": True,
        "max_results": 10,
        "topic": topic,
        "days": days,
        "include_domains": [target_website] if target_website else [],
        "exclude_domains": [],
    }

    try:
        # Use urllib.request.urlopen with explicit https scheme validation
        if not base_url.startswith(('https://', 'http://')):
            raise ValueError("URL scheme must be http or https")
            
        # Create a custom opener that only allows http and https schemes
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(base_url, data=data, headers=headers)
        handlers = []
        opener = urllib.request.build_opener(*handlers)
        opener.addheaders = list(headers.items())
        
        # Use the custom opener to open the URL
        with opener.open(request) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            print(f"Received {len(response_data.get('results', []))} results from Tavily AI search")
            return response_data
    except urllib.error.HTTPError as e:
        print(f"Failed to retrieve search results from Tavily AI Search, error: {e.code}, reason: {e.reason}")
        if hasattr(e, 'read'):
            error_content = e.read().decode('utf-8')
            print(f"Error details: {error_content}")
        return None

def save_to_s3(bucket, key, data):
    """Save data to S3 bucket."""
    s3_client = boto3.client('s3')
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
        print(f"Successfully saved data to s3://{bucket}/{key}")
    except Exception as e:
        print(f"Error saving to S3: {str(e)}")
