# Stock News Web Search

This project searches for stock news from the internet using the Tavily API for all 30 DJIA stocks and saves them to an S3 bucket. The solution is deployed as an AWS Lambda function that is triggered daily by EventBridge.

## Architecture

- **AWS Lambda**: Executes the Python code that searches for stock news and saves it to S3
- **Amazon EventBridge**: Triggers the Lambda function daily at midnight UTC for each stock ticker
- **Amazon S3**: Stores the fetched news data in JSON format
- **AWS Secrets Manager**: Securely stores the Tavily API key
- **IAM Roles and Policies**: Provides necessary permissions for Lambda to access S3 and Secrets Manager

## Features

- Searches for news for each stock ticker from the internet using Tavily API
- Filters news to include only today's news items
- Saves the filtered news to S3 with a structured path format
- Runs automatically every day for all 30 DJIA stocks (configurable)

## Configuration

The solution is parameterized with the following variables:

- `aws_region`: AWS region for deployment (default: us-east-1)
- `tickers`: List of stock ticker symbols (default: DJIA 30 stocks)
- `s3_bucket_prefix`: Prefix for S3 bucket name (default: stock-news-data)
- `tavily_api_key`: API key for Tavily web search service (required)

## Deployment

The infrastructure is deployed using Terraform with S3 backend. Before deploying, you need to:

1. Create the terraform.tfvars file with your desired values
2. Run the deployment script:
```bash
./deploy.sh
```

The deployment creates:

1. S3 bucket for storing news data
2. Secrets Manager secret for storing the Tavily API key
3. Lambda function with necessary IAM roles and policies
4. EventBridge rule to trigger the Lambda function daily for each ticker

## Usage

The Lambda function is triggered automatically every day at midnight UTC for each ticker. It will:

1. Search for news about each stock ticker from the internet using Tavily API
2. Filter the news to include only items published on the current date
3. Save the filtered news to the S3 bucket in the following path format:
   `{ticker}/{date}/market_news.json`


Make sure to set the required environment variables:
- `S3_BUCKET`: Name of the S3 bucket
- `DEFAULT_TICKER`: Default stock ticker symbol
- `TAVILY_API_KEY_NAME`: Name of the Secrets Manager secret containing the Tavily API key
