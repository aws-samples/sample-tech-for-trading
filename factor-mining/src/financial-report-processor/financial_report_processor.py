import json
import os
from io import BytesIO
import traceback

import boto3
import urllib.parse
import datetime
from clickhouse_driver import Client
import PyPDF2
import re
import logging
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
s3_client = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime')


CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST')
CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT', '9000'))
CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER')
CLICKHOUSE_SECRET_ARN = os.environ.get('CLICKHOUSE_SECRET_ARN')
CLICKHOUSE_DATABASE = os.environ.get('CLICKHOUSE_DATABASE')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')  # Default to Claude 3.7 Sonnet

# Factor type mapping
FACTOR_TYPE_MAPPING = {
    "CEO statement": "CEOS",
    "ESG initiatives": "ESGI",
    "Market trends and competitive landscape": "MTCI",
    "Risk factors": "RISK",
    "Strategic priorities": "STTG"
}


def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager without profile"""
    client = boto3.client(
        service_name='secretsmanager'
    )
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Secret retrieval error: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def extract_text_from_pdf(pdf_content):
    """Extract text from PDF content"""
    try:
        # If pdf_content is already a file-like object, use it directly
        if hasattr(pdf_content, 'read'):
            pdf_reader = PyPDF2.PdfReader(pdf_content)
        else:
            # Otherwise, wrap it in BytesIO
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        logger.info(f"PDF has {len(pdf_reader.pages)} pages")
        all_text = ""
        
        for page_num in range(len(pdf_reader.pages)):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                all_text += page_text + "\n"
                logger.info(f"Successfully extracted text from page {page_num+1}")
            except AttributeError as e:
                logger.error(f"AttributeError on page {page_num+1}: {str(e)}")
                logger.error(traceback.format_exc())
                all_text += f"[Content extraction failed for page {page_num+1}]\n"
            except Exception as e:
                logger.error(f"Error extracting text from page {page_num+1}: {str(e)}")
                logger.error(traceback.format_exc())
                all_text += f"[Content extraction failed for page {page_num+1}]\n"

        return all_text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def parse_bedrock_result(content):
    json_str = content[0]['text']
    # Clean up the JSON string by removing markdown code block markers
    if "```json" in json_str:
        json_str = json_str.split("```json", 1)[1]
    if "```" in json_str:
        json_str = json_str.split("```", 1)[0]
    # Parse the JSON
    data = json.loads(json_str)
    return data

def analyze_financial_report(text: str) -> Dict[str, Any]:
    """
    Analyze financial report text using Amazon Bedrock's Claude 3.7 Sonnet model.
    """
    try:
        # Prepare the prompt for the model
        # Limit text to 100k characters to fit within model context window
        prompt = f"""As an experience CFA and FRM holder, please analyze the attached annual report and extract concise summaries (2-3 sentences each) for the following key factors:

1. CEO statement - Focus on strategic vision, major achievements, and forward-looking statements
2. ESG initiatives - Highlight environmental sustainability efforts, social responsibility programs, and governance improvements
3. Market trends and competitive landscape - Identify industry shifts, market position changes, and competitive advantages/challenges
4. Risk factors - Extract the most significant financial, operational, and strategic risks facing the company
5. Strategic priorities - Summarize key growth initiatives, investment areas, and long-term business objectives

For each factor, provide:
- The most important points using specific data when available
- Any significant changes from the previous year
- A performance rating (0-10 scale) with brief justification based on industry benchmarks and year-over-year progress

Here is the financial report text:
<report>
{text[:100000]}  
</report>

Please output in the following JSON format:
{{
"items": [
{{
"category": "CEO statement",
"summary": "...",
"key_data": ["...", "..."],
"year_over_year_change": "...",
"rating": 8,
"rating_justification": "..."
}},
...
],
"overall_assessment": "...",
"investment_recommendation": "..."
}}

"""

        # Call Amazon Bedrock with Claude 3.7 Sonnet model using converse
        response = bedrock_runtime.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                            {
                                "text": prompt
                            }
                        ]
                }
            ],
            inferenceConfig={
                "maxTokens": 4000,
                "temperature": 0.2,
            }
        )
        
        # Parse the response
        content = response.get('output', {}).get('message', {}).get('content', '')
        
        # Extract JSON from the response
        items = parse_bedrock_result(content)
        return items
            
    except Exception as e:
        logger.error(f"Error calling Amazon Bedrock: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def save_to_clickhouse(analysis_result: Dict[str, Any], ticker: str, date_str: str):
    """Save factor ratings to Clickhouse"""
    try:
        # Parse date from string (format: YYYYMMDD)
        report_date = datetime.datetime.strptime(date_str, '%Y%m%d').date()
        
        # Connect to Clickhouse
        # Get credentials
        secret = get_secret(CLICKHOUSE_SECRET_ARN)

        client = Client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            user=CLICKHOUSE_USER,
            password=secret.get('password', ''),
            database=CLICKHOUSE_DATABASE
        )
        
        # Prepare data for insertion
        rows = []
        for item in analysis_result["items"]:
            factor_type = FACTOR_TYPE_MAPPING.get(item["category"])
            if factor_type:
                rows.append([
                    "GenAI",                  # factor_type
                    factor_type,             # factor_name
                    ticker,                       # ticker
                    report_date,                  # date
                    float(item["rating"]),        # value
                    datetime.datetime.now()       # update_time
                ])
        
        # Insert data into Clickhouse
        if rows:
            client.execute(
                'INSERT INTO factor_values (factor_type, factor_name, ticker, date, value, update_time) VALUES',
                rows
            )
            logger.info(f"Successfully inserted {len(rows)} rows into Clickhouse")
        
    except Exception as e:
        logger.error(f"Error saving to Clickhouse: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def lambda_handler(event, context):
    """Lambda handler function"""
    try:
        # Get the S3 bucket and key from the event
        bucket = event['Records'][0]['s3']['bucket']['name']
        OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET')
        if not OUTPUT_BUCKET:
            OUTPUT_BUCKET = bucket
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        
        # Check if the file is a PDF
        if not key.lower().endswith('.pdf'):
            logger.info(f"Skipping non-PDF file: {key}")
            return {
                'statusCode': 200,
                'body': json.dumps('Skipped non-PDF file')
            }
        
        # Extract ticker and date from the key
        # Expected format: ticker/year/YYYYMMDD.pdf
        path_parts = key.split('/')
        if len(path_parts) < 3:
            logger.error(f"Invalid file path format: {key}")
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid file path format')
            }
        
        ticker = path_parts[0]
        date_str = path_parts[2].split('.')[0]  # Remove .pdf extension
        
        # Get the PDF content
        response = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_content = response['Body'].read()
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_content)
        
        # Analyze the financial report
        analysis_result = analyze_financial_report(text)
        
        # Save the analysis result to S3
        output_key = key.replace('.pdf', '.json')
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=json.dumps(analysis_result),
            ContentType='application/json'
        )
        
        # Save factor ratings to Clickhouse
        save_to_clickhouse(analysis_result, ticker, date_str)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully processed financial report')
        }
        
    except Exception as e:
        logger.error(f"Error processing financial report: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
