resource "aws_iam_role" "role" {
  name               = var.role_name
  description        = var.role_description
  assume_role_policy = var.assume_role_policy
  path               = var.role_path
  max_session_duration = var.max_session_duration
  
  tags = var.tags
}

resource "aws_iam_policy" "policy" {
  count       = var.create_policy ? 1 : 0
  name        = var.policy_name
  description = var.policy_description
  policy      = var.policy_document
  path        = var.policy_path
  
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "custom_policy_attachment" {
  count      = var.create_policy ? 1 : 0
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.policy[0].arn
}

resource "aws_iam_role_policy_attachment" "managed_policy_attachments" {
  for_each   = toset(var.managed_policy_arns)
  role       = aws_iam_role.role.name
  policy_arn = each.value
}
