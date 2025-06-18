# Generate random ID for resource naming
resource "random_id" "clickhouse" {
  byte_length = 4
}

# IAM role for EC2 to access Secrets Manager
resource "aws_iam_role" "clickhouse_role" {
  name = "${var.project_name}-${var.environment}-clickhouse-role-${random_id.clickhouse.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-clickhouse-role-${random_id.clickhouse.hex}"
    Environment = var.environment
  }
}

# Create custom policy for Secrets Manager access
resource "aws_iam_policy" "secrets_access" {
  name = "${var.project_name}-${var.environment}-clickhouse-secrets-access-${random_id.clickhouse.hex}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [var.secret_arn]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = [var.kms_key_arn]
      }
    ]
  })
}

# Attach secrets policy to the IAM role
resource "aws_iam_role_policy_attachment" "secrets_access" {
  role       = aws_iam_role.clickhouse_role.name
  policy_arn = aws_iam_policy.secrets_access.arn
}

# Create instance profile
resource "aws_iam_instance_profile" "clickhouse_profile" {
  name = "${var.project_name}-${var.environment}-clickhouse-profile-${random_id.clickhouse.hex}"
  role = aws_iam_role.clickhouse_role.name
}

# Using security group IDs from the networking module instead of creating a new one

# Get latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Create user data script
locals {
  user_data = <<-EOF
    #!/bin/bash
    # Update system packages
    dnf update -y --skip-broken
    dnf install -y curl jq aws-cli --skip-broken

    # Set up logging
    exec > >(tee /var/log/clickhouse-bootstrap.log) 2>&1
    echo "Starting Clickhouse bootstrap script at $(date)"

    # Install Clickhouse
    echo "Installing Clickhouse..."
    curl https://clickhouse.com/ | sh
    sudo ./clickhouse install

    # Start ClickHouse Server
    echo "Starting Clickhouse server..."
    sudo clickhouse start

    # Wait for ClickHouse to start
    echo "Waiting for Clickhouse to start..."
    sleep 15

    # Get Clickhouse password from Secrets Manager
    SECRET_ARN="${var.secret_arn}"
    REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone | sed 's/[a-z]$//')
    echo "Retrieving secret from $SECRET_ARN in region $REGION"
    
    # Add retries and error handling
    MAX_RETRIES=5
    RETRY_COUNT=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
      SECRET_VALUE=$(aws secretsmanager get-secret-value --secret-id "$SECRET_ARN" --region "$REGION" --query SecretString --output text 2>/var/log/clickhouse-secret-error.log)
      if [ $? -eq 0 ] && [ ! -z "$SECRET_VALUE" ]; then
        echo "Successfully retrieved secret"
        break
      fi
      echo "Failed to retrieve secret, retrying in 5 seconds (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
      sleep 5
      RETRY_COUNT=$((RETRY_COUNT+1))
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
      echo "Failed to retrieve secret after $MAX_RETRIES attempts"
      # Use a hardcoded password as fallback
      echo "Using fallback password"
      CLICKHOUSE_PASSWORD="${var.clickhouse_password}"
    else
      # Extract password with error checking
      CLICKHOUSE_PASSWORD=$(echo $SECRET_VALUE | jq -r '.password')
      if [ -z "$CLICKHOUSE_PASSWORD" ] || [ "$CLICKHOUSE_PASSWORD" = "null" ]; then
        echo "Failed to extract password from secret, using fallback password"
        CLICKHOUSE_PASSWORD="${var.clickhouse_password}"
      fi
    fi

    echo "Password extracted successfully (length: $${#CLICKHOUSE_PASSWORD})"

    # Set default password for ClickHouse
    echo "Setting Clickhouse password..."
    sudo mkdir -p /etc/clickhouse-server/users.d/
    echo "<clickhouse><users><default><password>$CLICKHOUSE_PASSWORD</password></default></users></clickhouse>" | sudo tee /etc/clickhouse-server/users.d/default-password.xml
    sudo chown clickhouse:clickhouse /etc/clickhouse-server/users.d/default-password.xml
    sudo chmod 600 /etc/clickhouse-server/users.d/default-password.xml

    # Verify the password was set correctly
    echo "Password file created. Checking if password is set:"
    if grep -q "<password></password>" /etc/clickhouse-server/users.d/default-password.xml; then
      echo "ERROR: Password is empty! Setting it manually..."
      echo "<clickhouse><users><default><password>${var.clickhouse_password}</password></default></users></clickhouse>" | sudo tee /etc/clickhouse-server/users.d/default-password.xml
      sudo chown clickhouse:clickhouse /etc/clickhouse-server/users.d/default-password.xml
      sudo chmod 600 /etc/clickhouse-server/users.d/default-password.xml
    else
      echo "Password appears to be set correctly"
    fi

    # Configure Clickhouse to listen on all interfaces - FIX FOR CONNECTION ISSUES
    echo "Configuring Clickhouse to listen on all interfaces..."
    CONFIG_FILE="/etc/clickhouse-server/config.xml"
    
    # Backup the original config
    sudo cp $CONFIG_FILE $${CONFIG_FILE}.bak
    
    # Remove any existing listen_host lines
    sudo sed -i '/<listen_host>/d' $CONFIG_FILE
    
    # Insert the correct listen_host configuration after the </tcp_port> section
    sudo sed -i '/<\/tcp_port>/a \    <listen_host>0.0.0.0</listen_host>' $CONFIG_FILE
    
    echo "Updated Clickhouse configuration to listen on all interfaces"
    
    # Restart ClickHouse to apply changes
    echo "Restarting Clickhouse to apply changes..."
    sudo clickhouse restart

    # Wait for ClickHouse to restart
    echo "Waiting for Clickhouse to restart..."
    sleep 10
    
    # Verify that Clickhouse is listening on all interfaces
    echo "Verifying Clickhouse is listening on all interfaces:"
    netstat -tulpn | grep 9000 || echo "Clickhouse not listening on port 9000"
    
    # Create factor model database and tables
    echo "Creating factor model database and tables..."
    cat <<EOT | clickhouse-client --user default --password "$CLICKHOUSE_PASSWORD" --multiquery || echo "Failed to create database and tables"
    CREATE DATABASE IF NOT EXISTS factor_modeling_db;

    -- Create tick_data table
    CREATE TABLE IF NOT EXISTS factor_modeling_db.tick_data
    (
        symbol String,
        timestamp DateTime,
        open Float64,
        high Float64,
        low Float64,
        close Float64,
        volume UInt64,
        adjusted_close Float64
    )
    ENGINE = MergeTree
    ORDER BY (symbol, timestamp)
    SETTINGS index_granularity = 8192;

    -- Create factor_values table
    CREATE TABLE IF NOT EXISTS factor_modeling_db.factor_values
    (
        factor_type String,
        factor_name String,
        ticker String,
        date Date,
        value Float64,
        update_time DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (factor_type, factor_name, ticker, date)
    SETTINGS index_granularity = 8192;

    -- Create factor_details table
    CREATE TABLE IF NOT EXISTS factor_modeling_db.factor_details
    (
        factor_name String,
        factor_type String,
        test_date Date,
        ticker String,
        beta Float64,
        tstat Float64,
        pvalue Float64,
        rsquared Float64,
        conf_int_lower Float64,
        conf_int_upper Float64,
        update_time DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (factor_name, factor_type, test_date, ticker)
    SETTINGS index_granularity = 8192;

    -- Create factor_summary table
    CREATE TABLE IF NOT EXISTS factor_modeling_db.factor_summary
    (
        factor_name String,
        factor_type String,
        test_date Date,
        start_date Date,
        end_date Date,
        avg_beta Float64,
        avg_tstat Float64,
        avg_rsquared Float64,
        significant_stocks Int32,
        total_stocks Int32,
        annualized_return Float64,
        annualized_volatility Float64,
        sharpe_ratio Float64,
        max_drawdown Float64,
        description String,
        update_time DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (factor_type, factor_name, test_date)
    SETTINGS index_granularity = 8192;

    -- Create factor_timeseries table
    CREATE TABLE IF NOT EXISTS factor_modeling_db.factor_timeseries
    (
        factor_name String,
        factor_type String,
        date Date,
        factor_value Float64,
        high_portfolio_return Float64,
        low_portfolio_return Float64,
        update_time DateTime DEFAULT now()
    )
    ENGINE = MergeTree
    ORDER BY (factor_name, factor_type, date)
    SETTINGS index_granularity = 8192;

    -- Create stock_fundamental_factor_source
    CREATE TABLE IF NOT EXISTS factor_modeling_db.stock_fundamental_factors_source
    (
        -- Basic identifiers
        ticker String,                           -- Stock ticker symbol (e.g., AAPL, MSFT)
        cik String,                              -- SEC Central Index Key identifier with leading zeros (e.g., 0000320193)
        accession_number String,                 -- SEC submission number,
        end_date Date,                        -- Date of the financial report/statement (format: YYYY-MM-DD)
        filed_date Date,                        -- Date when the report was filed with SEC (format: YYYY-MM-DD)
        form String, -- Type of filing: 10-K (annual) or 10-Q (quarterly)
        fiscal_year UInt16,                      -- Fiscal year of the report (e.g., 2024)
        fiscal_quarter String,                    -- Fiscal quarter (Q1, Q2, Q3, Q4)
        
        -- Balance sheet metrics
        assets_current Decimal(20, 2),           -- Current assets in USD
        liabilities_current Decimal(20, 2),      -- Current liabilities in USD
        cash_and_equivalents Decimal(20, 2),     -- Cash and cash equivalents at carrying value in USD
        inventory_net Decimal(20, 2),            -- Net inventory in USD for current period
        inventory_net_prev_year Decimal(20, 2),  -- Net inventory in USD from previous year
        stockholders_equity Decimal(20, 2),      -- Total stockholders equity in USD
        
        -- Income statement metrics
        sales_revenue_net Decimal(20, 2),        -- Net sales revenue in USD for current period
        sales_revenue_net_prev_year Decimal(20, 2), -- Net sales revenue in USD from previous year
        cost_of_goods_sold Decimal(20, 2),       -- Cost of goods and services sold in USD
        interest_expense Decimal(20, 2),         -- Interest expense in USD
        income_before_taxes Decimal(20, 2),      -- Income before taxes, minority interest, and equity method investments in USD
        
        -- Metadata fields
        source_file String,                      -- Source file path or identifier (e.g., S3 path)
        processed_timestamp DateTime DEFAULT now(), -- Timestamp when the record was processed
        create_datetime DateTime DEFAULT now()   -- Timestamp when the record was created in the database
    )
    ENGINE = MergeTree()
    ORDER BY (ticker, end_date, filed_date)
    PARTITION BY toYYYYMM(end_date)
    SETTINGS index_granularity = 8192;
    EOT

    # Create systemd service file for Clickhouse
    echo "Creating systemd service file for Clickhouse..."
    cat <<EOT | sudo tee /etc/systemd/system/clickhouse-server.service
    [Unit]
    Description=ClickHouse Server
    After=network.target

    [Service]
    Type=forking
    User=clickhouse
    Group=clickhouse
    ExecStart=/usr/bin/clickhouse-server --config-file /etc/clickhouse-server/config.xml --pid-file /var/run/clickhouse-server/clickhouse-server.pid --daemon
    ExecStop=/usr/bin/clickhouse stop
    Restart=always
    LimitCORE=infinity
    LimitNOFILE=500000

    [Install]
    WantedBy=multi-user.target
    EOT

    # Enable and start Clickhouse service
    echo "Enabling Clickhouse to start on boot..."
    sudo systemctl daemon-reload
    sudo systemctl enable clickhouse-server
    sudo systemctl start clickhouse-server

    echo "Clickhouse bootstrap script completed at $(date)"
  EOF
}

# EC2 instance for Clickhouse
resource "aws_instance" "clickhouse" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_ids[0]
  vpc_security_group_ids = var.security_group_ids
  key_name               = var.key_name
  iam_instance_profile   = aws_iam_instance_profile.clickhouse_profile.name
  ebs_optimized          = true  # Enable EBS optimization for better performance
  
  root_block_device {
    volume_size = var.volume_size
    volume_type = "gp3"
    encrypted   = true
    tags = {
      Name        = "${var.project_name}-${var.environment}-clickhouse-data-${random_id.clickhouse.hex}"
      Environment = var.environment
    }
  }

  user_data = local.user_data

  tags = {
    Name        = "${var.project_name}-${var.environment}-clickhouse-${random_id.clickhouse.hex}"
    Environment = var.environment
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required" # Enforce IMDSv2
  }

  monitoring = true # Enable detailed monitoring
}
