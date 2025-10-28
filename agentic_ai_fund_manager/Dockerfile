FROM python:3.12-slim

ARG BWB_FUND_MANAGER_ARN
ARG BWB_MEMORY_ID
ARG BWB_AWS_REGION

ENV BWB_FUND_MANAGER_ARN=$BWB_FUND_MANAGER_ARN
ENV BWB_MEMORY_ID=$BWB_MEMORY_ID
ENV BWB_AWS_REGION=$BWB_AWS_REGION

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY fund_manager/app.py .
COPY static ./static

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health || exit 1


ENTRYPOINT [ "streamlit", "run", "app.py", \
             "--logger.level", "info", \
             "--browser.gatherUsageStats", "false", \
             "--browser.serverAddress", "0.0.0.0", \
             "--server.enableCORS", "false", \
             "--server.enableXsrfProtection", "false", \
             "--server.baseUrlPath", "/ia", \
             "--server.port", "80"]