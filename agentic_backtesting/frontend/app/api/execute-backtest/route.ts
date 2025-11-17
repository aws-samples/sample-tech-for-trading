import { NextRequest, NextResponse } from 'next/server';
import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agentcore';
import { v4 as uuidv4 } from 'uuid';

// Initialize AWS Bedrock AgentCore client
const client = new BedrockAgentCoreClient({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY
    ? {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      }
    : undefined, // Will use default credential chain if not provided
});

const AGENT_ARN = process.env.AGENTCORE_ARN!;

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  let sessionId: string | undefined;
  
  try {
    const strategyInput = await request.json();
    
    // Validate input
    if (!strategyInput || !strategyInput.name) {
      console.error('[AgentCore] Invalid strategy input:', strategyInput);
      return NextResponse.json(
        { success: false, error: 'Invalid strategy data provided' },
        { status: 400 }
      );
    }

    // Check if AgentCore ARN is configured
    if (!AGENT_ARN) {
      console.error('[AgentCore] ARN not configured');
      return NextResponse.json(
        { success: false, error: 'AgentCore ARN not configured. Set AGENTCORE_ARN in .env.local' },
        { status: 500 }
      );
    }
    
    // Generate unique session ID
    sessionId = uuidv4();
    
    // Format the prompt for your agent
    const prompt = `how is the strategy performance: ${JSON.stringify(strategyInput)}`;
    
    console.log('\n========================================');
    console.log('[AgentCore] PROMPT:');
    console.log('========================================');
    console.log(prompt);
    console.log('========================================\n');
    
    // Prepare payload
    const payload = Buffer.from(JSON.stringify({ prompt }));
    
    // Invoke the agent
    const command = new InvokeAgentRuntimeCommand({
      agentRuntimeArn: AGENT_ARN,
      runtimeSessionId: sessionId,
      payload: payload
    });
    
    const response = await client.send(command);
    
    // Process streaming response
    if (!response.response) {
      console.error('[AgentCore] No response received');
      return NextResponse.json(
        { success: false, error: 'No response from AgentCore' },
        { status: 500 }
      );
    }

    const chunks: Uint8Array[] = [];
    
    // Collect all chunks from the async iterator
    // @ts-ignore - AWS SDK types are complex, but this works at runtime
    for await (const chunk of response.response) {
      if (chunk) chunks.push(chunk);
    }
    
    // Concatenate all chunks
    const fullResponse = Buffer.concat(chunks).toString('utf-8');
    
    // Parse the response
    let result;
    try {
      result = JSON.parse(fullResponse);
    } catch (parseError) {
      console.error('[AgentCore] Failed to parse response');
      return NextResponse.json(
        { success: false, error: 'Failed to parse AgentCore response' },
        { status: 500 }
      );
    }
    
    // Extract the text content from the agent response
    if (!result.result?.content?.[0]?.text) {
      console.error('[AgentCore] Unexpected response structure');
      return NextResponse.json(
        { success: false, error: 'Unexpected response format from AgentCore' },
        { status: 500 }
      );
    }
    
    const textContent = result.result.content[0].text;
    
    console.log('========================================');
    console.log('[AgentCore] RESPONSE:');
    console.log('========================================');
    console.log(textContent);
    console.log('========================================\n');
    
    // Return formatted response
    return NextResponse.json({
      success: true,
      analysis: textContent,
      raw_response: result,
      session_id: sessionId
    });
    
  } catch (error: any) {
    console.error('\n========================================');
    console.error('[AgentCore] ERROR:');
    console.error('========================================');
    console.error(`${error.name || 'Error'}: ${error.message}`);
    console.error('========================================\n');
    
    // Handle specific AWS errors
    if (error.name === 'AccessDeniedException') {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Access denied. Check AWS credentials and IAM permissions.',
          error_type: 'AccessDeniedException'
        },
        { status: 403 }
      );
    }
    
    if (error.name === 'ResourceNotFoundException') {
      return NextResponse.json(
        { 
          success: false, 
          error: 'AgentCore agent not found. Check AGENTCORE_ARN in .env.local',
          error_type: 'ResourceNotFoundException'
        },
        { status: 404 }
      );
    }
    
    return NextResponse.json(
      {
        success: false,
        error: error.message || 'Failed to invoke AgentCore',
        error_type: error.name || 'UnknownError'
      },
      { status: 500 }
    );
  }
}

// Health check endpoint
export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    service: 'agentcore-api-route',
    agent_arn: AGENT_ARN ? '***configured***' : '***not configured***',
    aws_region: process.env.AWS_REGION || 'us-east-1'
  });
}
