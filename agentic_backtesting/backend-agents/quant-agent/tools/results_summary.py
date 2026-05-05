"""
Results Summary Tool
Generates comprehensive trading strategy reports using AgentCore Runtime
"""

import os
import json
import uuid
import time
from strands import tool
import config


@tool
def create_results_summary(backtest_results: dict) -> str:
    """
    Analyze backtest performance and generate comprehensive trading strategy report.

    Args:
        backtest_results: Dictionary containing backtest metrics and performance data

    Returns:
        Formatted analysis report with key statistics and performance assessment
    """
    agent_name = "📈 RESULTS SUMMARY AGENT"
    print("\n" + "="*50)
    print(agent_name)
    print("="*50)

    start_time = time.time()

    # If no backtest results provided, read from AgentCore Memory
    if backtest_results is None:
        print(f"📖 No backtest results provided, reading from AgentCore Memory...")
        backtest_results = config.get_backtest_results_from_memory()
        if backtest_results is None:
            return 'No backtest results found in AgentCore Memory'

    print(f"💾 AgentCore Memory: Processing stored results...")

    if 'error' in backtest_results:
        return f"Results in backtesting: {backtest_results['error']}"

    try:
        reasoning = "Analyzing backtest performance and generating summary..."

        print(f"📥 INPUT: {backtest_results}")
        print(f"🧠 REASONING: {reasoning}")

        result = config._agentcore_runtime_client.invoke_agent_runtime(
            agentRuntimeArn=os.getenv('BACKTEST_SUMMARY_RUNTIME_ARN'),
            runtimeSessionId=str(uuid.uuid4()),  # Unique session ID
            payload=json.dumps(backtest_results).encode('utf-8'),
            qualifier="DEFAULT"                  # Optional; version/endpoint control
        )

        # Parse the AgentCore runtime response
        if 'response' in result:
            response_body = result['response'].read().decode('utf-8')
            response_data = json.loads(response_body)

            # results_summary returns {"analysis": "...", "version": "..."}
            if isinstance(response_data, dict):
                summary_text = response_data.get('analysis', str(response_data))
                config._results_summary_version = response_data.get('version', 'unknown')
                print(f"📌 Results Summary Version: {config._results_summary_version}")
            else:
                summary_text = response_data

        elif 'body' in result:
            response_body = result['body'].read().decode('utf-8')
            response_data = json.loads(response_body)

            if 'result' in response_data and 'content' in response_data['result']:
                content = response_data['result']['content']
                if isinstance(content, list) and len(content) > 0:
                    summary_text = content[0].get('text', '')
                else:
                    summary_text = str(content)
            else:
                summary_text = response_body
        else:
            summary_text = str(result)

        processing_time = time.time() - start_time
        print(f"⏱️ Results summary completed in {processing_time:.2f} seconds")
        print(f"got JSON result: {summary_text}")

        # Brief pause to ensure completion
        time.sleep(0.5)
        return summary_text

    except Exception as e:
        processing_time = time.time() - start_time
        print(f"❌ Results summary failed after {processing_time:.2f} seconds: {e}")
        return f'Results processing failed: {str(e)}'
