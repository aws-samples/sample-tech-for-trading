#!/bin/bash

# Next.js Deployment Script for AgentCore Backtesting App
# Deploys to AWS S3 + CloudFront (Static Export)

set -e

echo "🚀 Next.js Deployment to AWS S3 + CloudFront"
echo "============================================="

# Configuration
BUCKET_NAME="${S3_BUCKET_NAME:-agentcore-nextjs-backtest-$(date +%s)}"
AWS_REGION="${AWS_REGION:-us-east-1}"
BUILD_DIR="out"
STACK_NAME="agentcore-nextjs-backtest-frontend"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first"
    exit 1
fi

if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "❌ Node.js/npm not found. Please install them first"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run: aws configure"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Temporarily modify next.config.js for static export
echo "⚙️ Configuring Next.js for static export..."
cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  images: {
    unoptimized: true,
  },
  // Disable features not supported in static export
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
}

module.exports = nextConfig
EOF

# Build application
echo "📦 Installing dependencies..."
npm install

echo "🔨 Building Next.js application (static export)..."
npm run build

if [ ! -d "$BUILD_DIR" ]; then
    echo "❌ Build failed - $BUILD_DIR directory not found"
    exit 1
fi

echo "✅ Build completed successfully"

# Check if CloudFormation stack exists
echo "🔍 Checking deployment status..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo "📊 Existing deployment found - updating..."
    
    # Get existing bucket name and distribution ID
    ACTUAL_BUCKET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
        --output text \
        --region "$AWS_REGION")
    
    DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
        --output text \
        --region "$AWS_REGION")
    
    echo "   Using existing bucket: $ACTUAL_BUCKET_NAME"
    echo "   Using existing CloudFront: $DISTRIBUTION_ID"
    
else
    echo "🆕 No existing deployment - creating new infrastructure..."
    
    # Create CloudFormation template
    cat > cloudformation-template.yaml << 'EOFCF'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'AgentCore Next.js Backtesting Frontend - S3 + CloudFront'

Parameters:
  BucketName:
    Type: String
    Description: Name for the S3 bucket
  
Resources:
  S3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref BucketName
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      VersioningConfiguration:
        Status: Enabled
      
  OriginAccessControl:
    Type: AWS::CloudFront::OriginAccessControl
    Properties:
      OriginAccessControlConfig:
        Name: !Sub "${BucketName}-OAC"
        OriginAccessControlOriginType: s3
        SigningBehavior: always
        SigningProtocol: sigv4
        Description: "OAC for AgentCore Next.js Backtesting"

  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Origins:
          - Id: S3Origin
            DomainName: !GetAtt S3Bucket.RegionalDomainName
            OriginAccessControlId: !GetAtt OriginAccessControl.Id
            S3OriginConfig: {}
        Enabled: true
        DefaultRootObject: index.html
        DefaultCacheBehavior:
          TargetOriginId: S3Origin
          ViewerProtocolPolicy: redirect-to-https
          CachePolicyId: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad
          OriginRequestPolicyId: 88a5eaf4-2fd4-4709-b370-b4c650ea3fcf
          ResponseHeadersPolicyId: 5cc3b908-e619-4b99-88e5-2cf7f45965bd
        CustomErrorResponses:
          - ErrorCode: 403
            ResponseCode: 200
            ResponsePagePath: /index.html
          - ErrorCode: 404
            ResponseCode: 200
            ResponsePagePath: /index.html
        PriceClass: PriceClass_100
        ViewerCertificate:
          CloudFrontDefaultCertificate: true

  BucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref S3Bucket
      PolicyDocument:
        Statement:
          - Sid: AllowCloudFrontServicePrincipal
            Effect: Allow
            Principal:
              Service: cloudfront.amazonaws.com
            Action: s3:GetObject
            Resource: !Sub "arn:aws:s3:::${S3Bucket}/*"
            Condition:
              StringEquals:
                "AWS:SourceArn": !Sub "arn:aws:cloudfront::${AWS::AccountId}:distribution/${CloudFrontDistribution}"

Outputs:
  BucketName:
    Description: Name of the S3 bucket
    Value: !Ref S3Bucket
    Export:
      Name: !Sub "${AWS::StackName}-BucketName"
      
  CloudFrontDistributionId:
    Description: CloudFront Distribution ID
    Value: !Ref CloudFrontDistribution
    Export:
      Name: !Sub "${AWS::StackName}-DistributionId"
      
  CloudFrontDomainName:
    Description: CloudFront Distribution Domain Name
    Value: !GetAtt CloudFrontDistribution.DomainName
    Export:
      Name: !Sub "${AWS::StackName}-DomainName"
      
  WebsiteURL:
    Description: Website URL
    Value: !Sub "https://${CloudFrontDistribution.DomainName}"
    Export:
      Name: !Sub "${AWS::StackName}-WebsiteURL"
EOFCF

    # Deploy CloudFormation stack
    echo "🚀 Creating infrastructure..."
    aws cloudformation deploy \
        --template-file cloudformation-template.yaml \
        --stack-name "$STACK_NAME" \
        --parameter-overrides BucketName="$BUCKET_NAME" \
        --capabilities CAPABILITY_IAM \
        --region "$AWS_REGION"

    # Get new stack outputs
    ACTUAL_BUCKET_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
        --output text \
        --region "$AWS_REGION")

    DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
        --output text \
        --region "$AWS_REGION")

    rm -f cloudformation-template.yaml
    echo "✅ Infrastructure created successfully"
fi

# Upload files to S3
echo "📤 Uploading files to S3..."

# Upload static assets with long cache
aws s3 sync "$BUILD_DIR/_next/static" "s3://$ACTUAL_BUCKET_NAME/_next/static" \
    --delete \
    --cache-control "public, max-age=31536000, immutable"

# Upload other files with shorter cache
aws s3 sync "$BUILD_DIR/" "s3://$ACTUAL_BUCKET_NAME" \
    --delete \
    --cache-control "public, max-age=0, must-revalidate" \
    --exclude "_next/static/*"

echo "✅ Files uploaded successfully"

# Invalidate CloudFront cache
echo "☁️ Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*"

echo "✅ CloudFront cache invalidated"

# Get final URLs
CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomainName`].OutputValue' \
    --output text \
    --region "$AWS_REGION")

WEBSITE_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
    --output text \
    --region "$AWS_REGION")

echo ""
echo "✅ Deployment completed successfully!"
echo "===================================="
echo ""
echo "🎯 Your AgentCore Next.js Backtesting app is live!"
echo ""
echo "📋 Access Information:"
echo "   Website URL: $WEBSITE_URL"
echo "   CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo "   S3 Bucket: $ACTUAL_BUCKET_NAME"
echo "   Distribution ID: $DISTRIBUTION_ID"
echo ""
echo "⚠️ Important Notes:"
echo "   - Next.js is deployed as a static export (no server-side features)"
echo "   - API routes run client-side via AWS SDK"
echo "   - Environment variables must be set at build time"
echo ""
echo "📋 Next steps:"
echo "1. Wait 5-10 minutes for CloudFront to fully deploy (first time only)"
echo "2. Visit: $WEBSITE_URL"
echo "3. Test the complete application workflow"
echo ""
echo "🔄 To update: Just run this script again after making changes"
echo ""
echo "🎉 Done!"
