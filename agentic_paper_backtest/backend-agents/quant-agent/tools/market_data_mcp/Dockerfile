FROM public.ecr.aws/lambda/python:3.12-x86_64

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code and environment configuration
COPY lambda_function.py ${LAMBDA_TASK_ROOT}
COPY deployment/.env ${LAMBDA_TASK_ROOT}/.env

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]
