variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}


variable "clickhouse_db_name" {
  description = "clickhouse db name"
  type        = string
  default     = "factor_modeling_db"
}


variable "tickers" {
  description = "List of stock ticker symbols (e.g. DJIA 30)"
  type        = list(string)
  default     = ["AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT"]
}

variable "cik_mapping" {
  description = "Mapping of ticker symbols to CIK numbers"
  type        = map(string)
  default     = {
    "AAPL" = "0000320193",
    "AMGN" = "0000318154",
    "AMZN" = "0001018724",
    "AXP"  = "0000004962",
    "BA"   = "0000012927",
    "CAT"  = "0000018230",
    "CRM"  = "0001108524",
    "CSCO" = "0000858877",
    "CVX"  = "0000093410",
    "DIS"  = "0001744489",
    "GS"   = "0000886982",
    "HD"   = "0000354950",
    "HON"  = "0000773840",
    "IBM"  = "0000051143",
    "JNJ"  = "0000200406",
    "JPM"  = "0000019617",
    "KO"   = "0000021344",
    "MCD"  = "0000063908",
    "MMM"  = "0000066740",
    "MRK"  = "0000310158",
    "MSFT" = "0000789019",
    "NKE"  = "0000320187",
    "NVDA" = "0001045810",
    "PG"   = "0000080424",
    "SHW"  = "0000089800",
    "TRV"  = "0000086312",
    "UNH"  = "0000731766",
    "V"    = "0001403161",
    "VZ"   = "0000732712",
    "WMT"  = "0000104169"
  }
}

variable "email" {
  description = "Email for SEC API user agent"
  type        = string
  default     = "your.email@example.com"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
