import { NextRequest, NextResponse } from 'next/server';
import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agentcore';
import { v4 as uuidv4 } from 'uuid';

const AGENT_ARN = process.env.AGENTCORE_ARN!;

function getClient() {
  return new BedrockAgentCoreClient({
    region: process.env.AWS_REGION || 'us-east-1',
  });
}

export async function POST(request: NextRequest) {
  try {
    const { prompt } = await request.json();

    if (!prompt?.trim()) {
      return NextResponse.json(
        { success: false, error: 'prompt is required' },
        { status: 400 }
      );
    }

    const client = getClient();
    const sessionId = uuidv4();

    const command = new InvokeAgentRuntimeCommand({
      agentRuntimeArn: AGENT_ARN,
      runtimeSessionId: sessionId,
      payload: Buffer.from(JSON.stringify({ mode: 'chat', prompt }))
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

    let result;
    try {
      result = JSON.parse(fullResponse);
    } catch {
      throw new Error('Failed to parse AgentCore response');
    }

    const text = result.result?.content?.[0]?.text || result.result || '';

    return NextResponse.json({ success: true, message: text });
  } catch (error: any) {
    console.error('[Chat API] Error:', error.message);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
