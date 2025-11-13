#!/bin/bash

# Next.js Deployment Script for AgentCore Backtesting App
# Supports Vercel (recommended) and AWS Amplify

set -e

echo "🚀 Next.js Deployment Script"
echo "============================"
echo ""

# Check prerequisites
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo "❌ Node.js/npm not found. Please install them first"
    exit 1
fi

# Ask deployment target
echo "Choose deployment target:"
echo "1) Vercel (Recommended - easiest)"
echo "2) AWS Amplify"
echo "3) Build only (for manual deployment)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📦 Deploying to Vercel..."
        echo "========================"
        echo ""
        
        # Check if Vercel CLI is installed
        if ! command -v vercel &> /dev/null; then
            echo "📥 Installing Vercel CLI..."
            npm install -g vercel
        fi
        
        echo "✅ Vercel CLI ready"
        echo ""
        echo "🔐 Important: Set these environment variables in Vercel dashboard:"
        echo "   - AWS_REGION=us-east-1"
        echo "   - AGENTCORE_ARN=arn:aws:bedrock-agentcore:us-east-1:600627331406:runtime/quant_agent-D6li6lBv47"
        echo "   - AWS_ACCESS_KEY_ID=your_key"
        echo "   - AWS_SECRET_ACCESS_KEY=your_secret"
        echo ""
        read -p "Press Enter when environment variables are set..."
        
        echo ""
        echo "🚀 Deploying to Vercel..."
        vercel --prod
        
        echo ""
        echo "✅ Deployment complete!"
        echo "🌐 Your app is now live on Vercel"
        ;;
        
    2)
        echo ""
        echo "📦 Deploying to AWS Amplify..."
        echo "=============================="
        echo ""
        
        if ! command -v aws &> /dev/null; then
            echo "❌ AWS CLI not found. Please install it first"
            exit 1
        fi
        
        if ! aws sts get-caller-identity &> /dev/null; then
            echo "❌ AWS credentials not configured. Please run: aws configure"
            exit 1
        fi
        
        echo "📋 AWS Amplify Deployment Steps:"
        echo ""
        echo "1. Go to AWS Amplify Console: https://console.aws.amazon.com/amplify/"
        echo "2. Click 'New app' → 'Host web app'"
        echo "3. Connect your GitHub repository"
        echo "4. Framework: Next.js SSR"
        echo "5. Build settings (auto-detected):"
        echo "   - Build command: npm run build"
        echo "   - Output directory: .next"
        echo "6. Add environment variables:"
        echo "   - AWS_REGION=us-east-1"
        echo "   - AGENTCORE_ARN=arn:aws:bedrock-agentcore:us-east-1:600627331406:runtime/quant_agent-D6li6lBv47"
        echo "   - AWS_ACCESS_KEY_ID=your_key (or use IAM role)"
        echo "   - AWS_SECRET_ACCESS_KEY=your_secret (or use IAM role)"
        echo "7. Click 'Save and deploy'"
        echo ""
        echo "✅ Follow the steps above to complete deployment"
        ;;
        
    3)
        echo ""
        echo "🔨 Building for production..."
        echo "============================"
        echo ""
        
        echo "📦 Installing dependencies..."
        npm install
        
        echo "🔨 Building Next.js app..."
        npm run build
        
        echo ""
        echo "✅ Build complete!"
        echo "📁 Build output in: .next/"
        echo ""
        echo "📋 Manual deployment options:"
        echo "1. Vercel: Run 'vercel --prod'"
        echo "2. AWS Amplify: Upload to Amplify Console"
        echo "3. Docker: Create Dockerfile and deploy to ECS/EKS"
        echo "4. Static export: Add 'output: export' to next.config.js"
        ;;
        
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Done!"
