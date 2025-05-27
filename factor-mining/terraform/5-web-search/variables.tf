# Variables
variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "tickers" {
  description = "List of stock ticker symbols (e.g. DJIA 30)"
  type        = list(string)
  default     = ["AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT"]
}

variable "s3_bucket_prefix" {
  description = "Prefix for S3 bucket name"
  type        = string
  default     = "stock-news-data"
}

variable "tavily_api_key" {
  description = "API key for Tavily web search service"
  type        = string
  sensitive   = true
  # This will be provided via environment variable TF_VAR_tavily_api_key
}
