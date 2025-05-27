# Factor Mining Visualization

This directory contains a Streamlit application for visualizing factor mining results.

## Features

- Display factor mining result summary for each factor and test date
- Visualize how `thread_no` and `parallel_m` impact the Step Function runtime
- Filter results by factor type, factor name, start date, end date, and test date
- Interactive visualizations for performance metrics

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```
   export CLICKHOUSE_HOST=
   export CLICKHOUSE_PORT=9000
   export CLICKHOUSE_USER=default
   export CLICKHOUSE_PASSWORD=
   export CLICKHOUSE_DATABASE=factor_model_tick_data_database
   export AWS_REGION=us-east-1
   export STATE_MACHINE_ARN=arn:aws:states:us-east-1:xyz
   ```

3. Run the application:
   ```
   ./run_local.sh
   ```

## Docker Deployment

1. Build the Docker image:
   ```
   docker build -t factor-mining-visualization .
   ```

2. Run the container:
   ```
   docker run -p 8501:8501 factor-mining-visualization
   ```

## AWS Deployment

The application can be deployed to AWS using the Terraform configuration in `terraform/7-visualization`.

1. Navigate to the Terraform directory:
   ```
   cd ../../terraform/7-visualization
   ```

2. Run the deployment script:
   ```
   ./deploy.sh
   ```

## AWS Authentication

The application uses the AWS SDK to fetch Step Function execution data. Make sure to configure AWS credentials with the appropriate permissions.

When running locally, you can use the AWS CLI profile:
```
aws configure --profile factor
```

When deployed to AWS, the application will use the IAM role assigned to the ECS task.
