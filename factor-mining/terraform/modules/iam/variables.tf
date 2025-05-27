variable "role_name" {
  description = "Name of the IAM role"
  type        = string
}

variable "role_description" {
  description = "Description of the IAM role"
  type        = string
  default     = ""
}

variable "assume_role_policy" {
  description = "Policy document for the assume role policy"
  type        = string
}

variable "role_path" {
  description = "Path for the IAM role"
  type        = string
  default     = "/"
}

variable "max_session_duration" {
  description = "Maximum session duration in seconds"
  type        = number
  default     = 3600
}

variable "create_policy" {
  description = "Whether to create a custom policy"
  type        = bool
  default     = false
}

variable "policy_name" {
  description = "Name of the IAM policy"
  type        = string
  default     = ""
}

variable "policy_description" {
  description = "Description of the IAM policy"
  type        = string
  default     = ""
}

variable "policy_document" {
  description = "Policy document for the IAM policy"
  type        = string
  default     = ""
}

variable "policy_path" {
  description = "Path for the IAM policy"
  type        = string
  default     = "/"
}

variable "managed_policy_arns" {
  description = "List of managed policy ARNs to attach to the role"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}
