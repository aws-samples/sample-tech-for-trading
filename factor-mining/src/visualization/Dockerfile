FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Set environment variables
ENV CLICKHOUSE_HOST=44.222.122.134
ENV CLICKHOUSE_PORT=9000
ENV CLICKHOUSE_USER=default
ENV CLICKHOUSE_PASSWORD=clickhouse@aws
ENV CLICKHOUSE_DATABASE=factor_model_tick_data_database
ENV AWS_REGION=us-east-1
ENV STATE_MACHINE_ARN=arn:aws:states:us-east-1:600627331406:stateMachine:factor-modeling-workflow

# Command to run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
