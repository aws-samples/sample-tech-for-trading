# IAM Role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-lambda-policy"
  description = "Policy for Factor Modeling Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda function for processing date, ticker, and thread
resource "aws_lambda_function" "process_date_ticker_thread" {
  function_name    = "${var.project_name}-process-date-ticker-thread"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  handler          = "process_date_ticker_thread.lambda_handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_role.arn
}

# Lambda function for processing results
resource "aws_lambda_function" "process_results" {
  function_name    = "${var.project_name}-process-batch-results"
  filename         = data.archive_file.results_lambda_zip.output_path
  source_code_hash = data.archive_file.results_lambda_zip.output_base64sha256
  handler          = "process_results.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128
  role             = aws_iam_role.lambda_role.arn
}

# Lambda function for error handling
resource "aws_lambda_function" "handle_error" {
  function_name    = "${var.project_name}-handle-error"
  filename         = data.archive_file.error_lambda_zip.output_path
  source_code_hash = data.archive_file.error_lambda_zip.output_base64sha256
  handler          = "handle_error.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128
  role             = aws_iam_role.lambda_role.arn
}

# Zip the Lambda function code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.root}/../../src/step-function/process_date_ticker_thread.py"
  output_path = "${path.module}/lambda/process_date_ticker_thread.zip"
}

# Zip results Lambda code
data "archive_file" "results_lambda_zip" {
  type        = "zip"
  source_file = "${path.root}/../../src/step-function/process_results.py"
  output_path = "${path.module}/lambda/process_results.zip"
}

# Zip error handling Lambda code
data "archive_file" "error_lambda_zip" {
  type        = "zip"
  source_file = "${path.root}/../../src/step-function/handle_error.py"
  output_path = "${path.module}/lambda/handle_error.zip"
}

# IAM Role for Step Function
resource "aws_iam_role" "step_function_role" {
  name = "${var.project_name}-step-function-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Step Function
resource "aws_iam_policy" "step_function_policy" {
  name        = "${var.project_name}-step-function-policy"
  description = "Policy for Factor Modeling Step Function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "lambda:InvokeFunction"
        ]
        Effect   = "Allow"
        Resource = [
          aws_lambda_function.process_date_ticker_thread.arn,
          aws_lambda_function.process_results.arn,
          aws_lambda_function.handle_error.arn
        ]
      },
      {
        Action = [
          "batch:SubmitJob",
          "batch:DescribeJobs",
          "batch:TerminateJob"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule"
        ],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}

# Attach policy to Step Function role
resource "aws_iam_role_policy_attachment" "step_function_policy_attachment" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_policy.arn
}

# Step Function definition
resource "aws_sfn_state_machine" "factor_modeling_workflow" {
  name     = "${var.project_name}-workflow"
  role_arn = aws_iam_role.step_function_role.arn

  definition = templatefile("${path.module}/stepfunction-definition.tftpl", {
    ProcessDateTickerThreadLambdaArn = aws_lambda_function.process_date_ticker_thread.arn,
    ProcessResultsLambdaArn = aws_lambda_function.process_results.arn,
    HandleErrorLambdaArn = aws_lambda_function.handle_error.arn,
    BatchJobQueueArn = var.batch_job_queue_arn,
    BatchJobDefinitionName = var.batch_job_definition_name
  })
}
