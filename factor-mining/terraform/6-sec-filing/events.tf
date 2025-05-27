# EventBridge rule to trigger sec_data_lambda daily
resource "aws_cloudwatch_event_rule" "daily_sec_data_trigger" {
  name                = "daily-sec-filing-trigger_${random_id.suffix.hex}"
  description         = "Triggers SEC data Lambda function daily"
  schedule_expression = "cron(0 1 * * ? *)" # Run at 1 AM UTC every day
}

# EventBridge target for sec_data_lambda
resource "aws_cloudwatch_event_target" "sec_data_lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_sec_data_trigger.name
  target_id = "sec_data_lambda_${random_id.suffix.hex}"
  arn       = aws_lambda_function.sec_data_lambda.arn
}

# Permission for EventBridge to invoke sec_data_lambda
resource "aws_lambda_permission" "allow_eventbridge_sec_data" {
  statement_id  = "AllowExecutionFromEventBridge_${random_id.suffix.hex}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sec_data_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_sec_data_trigger.arn
}

# S3 event notification to trigger extract_sec_lambda
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.sec_data_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.extract_sec_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [
    aws_lambda_permission.allow_s3_extract_sec
  ]
}

# Permission for S3 to invoke extract_sec_lambda
resource "aws_lambda_permission" "allow_s3_extract_sec" {
  statement_id  = "AllowExecutionFromS3Bucket_${random_id.suffix.hex}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.extract_sec_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.sec_data_bucket.arn
}
