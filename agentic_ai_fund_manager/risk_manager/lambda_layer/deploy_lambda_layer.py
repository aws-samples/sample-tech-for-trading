"""
deploy_lambda_layer.py

Lambda Layer Deployment Script
Deploy Lambda Layer including yfinance library
"""

import boto3
import json
import time
import os
import sys
from pathlib import Path

# Add common configuration path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))
from config import Config as GlobalConfig

class Config:
    """Lambda Layer deployment configuration"""
    REGION = GlobalConfig.REGION
    LAYER_NAME = GlobalConfig.LAMBDA_LAYER_NAME

def get_account_id():
    """Return the AWS account ID of the current credentials"""
    sts_client = boto3.client('sts', region_name=Config.REGION)
    return sts_client.get_caller_identity()["Account"]

def setup_s3_bucket(account_id):
    """Set up S3 bucket, failing closed if the name is owned by another account.

    The bucket name is predictable, so anyone can pre-create it. A successful
    head_bucket only proves we can access the bucket, not that we own it, so
    every check pins ExpectedBucketOwner to our account.
    """
    print("📦 Setting up S3 bucket...")
    s3_client = boto3.client('s3', region_name=Config.REGION)
    bucket_name = f"{Config.LAYER_NAME}-{account_id}"

    try:
        s3_client.head_bucket(Bucket=bucket_name, ExpectedBucketOwner=account_id)
        return bucket_name

    except s3_client.exceptions.ClientError as e:
        code = e.response['Error']['Code']
        if code == '403':
            raise RuntimeError(
                f"S3 bucket {bucket_name} exists but is not owned by account {account_id}. "
                "Refusing to use it."
            ) from e
        if code != '404':
            raise

    try:
        if Config.REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': Config.REGION}
            )
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        pass
    except s3_client.exceptions.BucketAlreadyExists as e:
        raise RuntimeError(
            f"S3 bucket {bucket_name} was created by another account. Refusing to use it."
        ) from e
    return bucket_name

def upload_layer_zip(zip_file_path, bucket_name, account_id):
    """Upload Layer ZIP file to S3 (only if the bucket is still owned by us)"""
    s3_client = boto3.client('s3', region_name=Config.REGION)
    object_key = f"{Config.LAYER_NAME}.zip"

    s3_client.upload_file(
        zip_file_path, bucket_name, object_key,
        ExtraArgs={'ExpectedBucketOwner': account_id}
    )
    return object_key

def create_lambda_layer(bucket_name, s3_key):
    """Create Lambda Layer"""
    print("🔧 Creating Lambda Layer...")
    lambda_client = boto3.client('lambda', region_name=Config.REGION)
    
    response = lambda_client.publish_layer_version(
        LayerName=Config.LAYER_NAME,
        Content={
            'S3Bucket': bucket_name,
            'S3Key': s3_key
        },
        CompatibleRuntimes=["python3.12"],
        CompatibleArchitectures=['x86_64']
    )
    
    return {
        'layer_arn': response['LayerArn'],
        'layer_version_arn': response['LayerVersionArn'],
        'version': response['Version']
    }

def save_deployment_info(result):
    """Save deployment information"""
    info_file = Path(__file__).parent / "layer_deployment_info.json"
    with open(info_file, 'w') as f:
        json.dump(result, f, indent=2)
    return str(info_file)

def main():
    try:
        print("🚀 yfinance Lambda Layer Deployment")
        
        # Check ZIP file
        current_dir = Path(__file__).parent
        zip_file = current_dir / f"{Config.LAYER_NAME}.zip"
        
        if not zip_file.exists():
            print(f"❌ Layer ZIP file not found: {zip_file}")
            print(f"💡 Please place {Config.LAYER_NAME}.zip file in the current directory.")
            raise FileNotFoundError(f"Layer ZIP file not found: {Config.LAYER_NAME}.zip")
        
        # Set up S3 bucket
        account_id = get_account_id()
        bucket_name = setup_s3_bucket(account_id)

        # Upload ZIP file
        s3_key = upload_layer_zip(str(zip_file), bucket_name, account_id)
        
        # Create Lambda Layer
        layer_result = create_lambda_layer(bucket_name, s3_key)
        
        # Configure deployment result
        result = {
            'layer_name': Config.LAYER_NAME,
            'layer_arn': layer_result['layer_arn'],
            'layer_version_arn': layer_result['layer_version_arn'],
            'version': layer_result['version'],
            's3_bucket': bucket_name,
            's3_key': s3_key,
            'region': Config.REGION,
            'runtime': "python3.12",
            'deployed_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save deployment information
        info_file = save_deployment_info(result)
        
        print(f"\n🎉 Lambda Layer Deployment Complete!")
        print(f"🔗 Layer Version ARN: {result['layer_version_arn']}")
        print(f"📄 Deployment Info: {info_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Lambda Layer Deployment Failed: {e}")
        raise

if __name__ == "__main__":
    main()