# Financial Report Processor

This module contains the Lambda function code for processing financial reports and extracting factors using Amazon Bedrock.

## Overview

The Lambda function:
1. Is triggered when a new PDF is uploaded to an S3 bucket
2. Extracts text from the PDF
3. Sends the text to Amazon Bedrock (Claude 3 Sonnet model) with a specific prompt to extract key factors
4. Saves the analysis results as JSON in the same S3 bucket
5. Stores factor ratings in a Clickhouse database

## Factors Extracted

The function extracts the following factors from financial reports:

1. CEO statement (CEOS) - Strategic vision, major achievements, and forward-looking statements
2. ESG initiatives (ESGI) - Environmental sustainability, social responsibility, and governance
3. Market trends and competitive landscape (MTCI) - Industry shifts and competitive position
4. Risk factors (RISK) - Financial, operational, and strategic risks
5. Strategic priorities (STTG) - Growth initiatives and long-term objectives

## Amazon Bedrock Integration

The function uses Amazon Bedrock's Claude 3 Sonnet model to analyze financial reports. The model is provided with a specific prompt that instructs it to extract key factors and provide ratings on a 0-10 scale.

The prompt includes instructions to format the response as JSON, which is then parsed and processed by the Lambda function.

## Development

### Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Testing with S3 files:
   ```
   python test_financial_report_processor.py <bucket_name> <file_key>
   ```
   Example:
   ```
   python test_financial_report_processor.py financial-reports-bucket AMZN/2025/20250510.pdf
   ```

3. Testing with local PDF files:
   ```
   python test_local_pdf.py <path_to_pdf> [ticker] [date]
   ```
   Example:
   ```
   python test_local_pdf.py ./annual_report.pdf AMZN 20250510
   ```

### Deployment

The function is deployed using Terraform. See the `terraform/8-financial-report-processor` directory for deployment instructions.

## Implementation Notes

- The function expects financial reports to be uploaded to the S3 bucket with the structure: `{bucket_name}/{ticker}/{year}/{YYYYMMDD}.pdf`
- The function has a fallback mechanism that returns mock data if the Bedrock API call fails
- The text extracted from the PDF is limited to 100,000 characters to fit within the model's context window
