# Financial Report Processor

This module deploys the infrastructure for processing financial reports. It includes:

1. Lambda function for processing financial reports
2. S3 bucket for storing financial reports
3. IAM roles and policies for secure access
4. VPC integration for secure network access

## Dependencies

This module depends on:
- The shared Clickhouse Lambda layer from the `0-prepare` module
- VPC and networking from the `1-networking` module
- Clickhouse database and secrets from the `2-clickhouse` module


## Deployment

To deploy this module:

1. Create the terraform.tfvars file with your desired values
2. Then deploy this module:
   ```bash
   cd ../7-financial-report
   ./deploy.sh
   ```


## S3 Bucket Structure

The financial reports must be uploaded to the S3 bucket following this structure:
```
s3://your-financial-reports-bucket/ticker/year/YYYYMMDD.pdf
```

For example:
```
s3://your-financial-reports-bucket/AAPL/2023/20230228.pdf
s3://your-financial-reports-bucket/MSFT/2024/20240131.pdf
```

This structure allows the Lambda function to properly process and organize the financial reports by company ticker and reporting period.
