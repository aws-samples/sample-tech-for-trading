import { NextRequest, NextResponse } from 'next/server';
import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agentcore';
import { v4 as uuidv4 } from 'uuid';

const AGENT_ARN = process.env.AGENTCORE_ARN!;

// In-memory store (use Redis/DynamoDB in production)
const results = new Map<string, any>();

function getClient() {
  return new BedrockAgentCoreClient({
    region: process.env.AWS_REGION || 'us-east-1',
  });
}

export async function POST(request: NextRequest) {
  try {
    const strategyInput = await request.json();
    const jobId = uuidv4();
    
    // Start async processing
    processBacktest(jobId, strategyInput);
    
    // Return immediately with job ID
    return NextResponse.json({ 
      success: true, 
      jobId,
      message: 'Backtest started. Poll /api/backtest-status/{jobId} for results.'
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

async function processBacktest(jobId: string, strategyInput: any) {
  results.set(jobId, { status: 'processing' });
  
  try {
    const client = getClient();
    const sessionId = uuidv4();
    const prompt = `how is the strategy performance: ${JSON.stringify(strategyInput)}`;
    
    console.log('========================================');
    console.log('[AgentCore] PROMPT:');
    console.log('========================================');
    console.log(prompt);
    console.log('========================================');
    
    const command = new InvokeAgentRuntimeCommand({
      agentRuntimeArn: AGENT_ARN,
      runtimeSessionId: sessionId,
      payload: Buffer.from(JSON.stringify({ prompt }))
    });
    
    const response = await client.send(command);
    
    if (!response.response) {
      throw new Error('No response from AgentCore');
    }

    const chunks: Uint8Array[] = [];
    // @ts-ignore
    for await (const chunk of response.response) {
      if (chunk) chunks.push(chunk);
    }

    const fullResponse = Buffer.concat(chunks).toString('utf-8');
    
    console.log('========================================');
    console.log('[AgentCore] RAW RESPONSE:');
    console.log('========================================');
    console.log(fullResponse);
    console.log('========================================');
    
    // Parse the response
    let result;
    try {
      result = JSON.parse(fullResponse);
    } catch (parseError) {
      throw new Error('Failed to parse AgentCore response');
    }
    
    // Extract the text content from the agent response
    if (!result.result?.content?.[0]?.text) {
      throw new Error('Unexpected response format from AgentCore');
    }
    
    const analysisText = result.result.content[0].text;
    
    console.log('========================================');
    console.log('[AgentCore] EXTRACTED TEXT:');
    console.log('========================================');
    console.log(analysisText);
    console.log('========================================');
    
    results.set(jobId, {
      status: 'complete',
      data: {
        success: true,
        analysis: analysisText,
        strategyInput
      }
    });
  } catch (error: any) {
    console.log('========================================');
    console.log('[AgentCore] ERROR:');
    console.log('========================================');
    console.log(error.message);
    console.log('========================================');
    
    results.set(jobId, {
      status: 'error',
      error: error.message
    });
  }
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const jobId = url.searchParams.get('jobId');
  
  if (!jobId) {
    return NextResponse.json({ error: 'jobId required' }, { status: 400 });
  }
  
  const result = results.get(jobId);
  if (!result) {
    return NextResponse.json({ error: 'Job not found' }, { status: 404 });
  }
  
  return NextResponse.json(result);
}
