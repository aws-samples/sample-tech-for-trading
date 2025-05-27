output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.financial_report_processor.arn
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for financial reports"
  value       = aws_s3_bucket.financial_reports.id
}
