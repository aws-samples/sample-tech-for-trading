#!/bin/bash
# Infrastructure deployment - creates or updates CloudFormation stack
set -e

echo "☁️  Infrastructure Deployment"
echo "============================="

if [ -f .env.local ]; then
    export $(grep -v '^#' .env.local | grep -v '^$' | xargs)
fi

if [ -z "$AGENTCORE_ARN" ]; then
    echo "❌ AGENTCORE_ARN not set in .env.local"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.us-east-2.amazonaws.com/agentcore-backtest-ecr"
STACK_NAME="agentcore-backtest-v2"

# CloudFront origin-facing managed prefix list for this region
CF_PREFIX_LIST_ID=$(aws ec2 describe-managed-prefix-lists \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --region us-east-2 \
  --query 'PrefixLists[0].PrefixListId' --output text)

# Secret header CloudFront adds; ALB only forwards requests carrying it.
# Persisted in SSM so stack updates reuse the same value.
ORIGIN_VERIFY_SECRET=$(aws ssm get-parameter --name /agentcore-backtest/origin-verify-secret \
  --with-decryption --region us-east-2 --query 'Parameter.Value' --output text 2>/dev/null || true)
if [ -z "$ORIGIN_VERIFY_SECRET" ]; then
    ORIGIN_VERIFY_SECRET=$(openssl rand -hex 32)
    aws ssm put-parameter --name /agentcore-backtest/origin-verify-secret \
      --value "$ORIGIN_VERIFY_SECRET" --type SecureString --region us-east-2 > /dev/null
    echo "🔐 Generated new origin-verify secret (stored in SSM)"
fi

echo "📋 Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file ecs-cloudformation.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides \
    ServiceName="agentcore-backtest" \
    ImageUri="$ECR_URI:latest" \
    AgentCoreArn="$AGENTCORE_ARN" \
    CloudFrontPrefixListId="$CF_PREFIX_LIST_ID" \
    OriginVerifySecret="$ORIGIN_VERIFY_SECRET" \
  --capabilities CAPABILITY_IAM \
  --region us-east-2

echo ""
echo "⚙️  Configuring timeouts..."

# Configure ALB timeout
ALB_ARN=$(aws cloudformation describe-stack-resources \
  --stack-name "$STACK_NAME" \
  --region us-east-2 \
  --query 'StackResources[?ResourceType==`AWS::ElasticLoadBalancingV2::LoadBalancer`].PhysicalResourceId' \
  --output text)

aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn "$ALB_ARN" \
  --attributes Key=idle_timeout.timeout_seconds,Value=300 \
  --region us-east-2 > /dev/null

# Configure CloudFront timeout
DIST_ID=$(aws cloudformation describe-stack-resources \
  --stack-name "$STACK_NAME" \
  --region us-east-2 \
  --query 'StackResources[?ResourceType==`AWS::CloudFront::Distribution`].PhysicalResourceId' \
  --output text)

aws cloudfront get-distribution-config --id "$DIST_ID" --query 'DistributionConfig' --output json > /tmp/cf-config.json
ETAG=$(aws cloudfront get-distribution-config --id "$DIST_ID" --query 'ETag' --output text)
jq '.Origins.Items[0].CustomOriginConfig.OriginReadTimeout = 60 | .Origins.Items[0].CustomOriginConfig.OriginKeepaliveTimeout = 60' /tmp/cf-config.json > /tmp/cf-config-updated.json
aws cloudfront update-distribution --id "$DIST_ID" --distribution-config file:///tmp/cf-config-updated.json --if-match "$ETAG" > /dev/null

echo ""
echo "✅ Infrastructure deployed!"

CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region us-east-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontUrl`].OutputValue' \
  --output text)

echo ""
echo "🌐 App URL: https://$CLOUDFRONT_URL"
