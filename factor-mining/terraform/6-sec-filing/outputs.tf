output "sec_data_bucket_name" {
  description = "Name of the S3 bucket storing SEC data"
  value       = aws_s3_bucket.sec_data_bucket.id
}

output "sec_data_lambda_function_name" {
  description = "Name of the Lambda function collecting SEC data"
  value       = aws_lambda_function.sec_data_lambda.function_name
}

output "extract_sec_lambda_function_name" {
  description = "Name of the Lambda function extracting SEC data"
  value       = aws_lambda_function.extract_sec_lambda.function_name
}

output "sec_data_lambda_arn" {
  description = "ARN of the Lambda function collecting SEC data"
  value       = aws_lambda_function.sec_data_lambda.arn
}

output "extract_sec_lambda_arn" {
  description = "ARN of the Lambda function extracting SEC data"
  value       = aws_lambda_function.extract_sec_lambda.arn
}
