import boto3


def get_prompt_management_response(prompt_id, variable_key, variable_value):
    """Get a response from the Bedrock Prompt Management using specified parameters."""

    # Create a Boto3 client for the Bedrock Runtime service
    session = boto3.Session()
    bedrock = session.client(service_name='bedrock-runtime', region_name='us-west-2')

    # Invoke the Bedrock Prompt Management
    response = bedrock.converse(
        modelId=prompt_id,
        promptVariables={
            variable_key: {"text": variable_value}
        }
    )

    return response
