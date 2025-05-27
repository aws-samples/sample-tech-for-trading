output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.market_data_processor.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function"
  value       = aws_lambda_function.market_data_processor.arn
}

output "lambda_signing_job_id" {
  description = "ID of the signing job for the Lambda function"
  value       = aws_signer_signing_job.lambda_code_signing.job_id
}

output "lambda_signed_object_key" {
  description = "S3 key of the signed Lambda function code"
  value       = aws_signer_signing_job.lambda_code_signing.signed_object[0].s3[0].key
}
