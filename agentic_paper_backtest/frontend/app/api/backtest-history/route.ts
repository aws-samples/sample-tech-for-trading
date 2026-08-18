import { NextRequest, NextResponse } from 'next/server';
import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agentcore';
import { v4 as uuidv4 } from 'uuid';

const AGENT_ARN = process.env.AGENTCORE_ARN!;

function getClient() {
  return new BedrockAgentCoreClient({
    region: process.env.AWS_REGION || 'us-east-1',
  });
}

export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const symbol = url.searchParams.get('symbol') || undefined;
    const limit = parseInt(url.searchParams.get('limit') || '10');

    const client = getClient();
    const sessionId = uuidv4();
    const prompt = JSON.stringify({
      action: 'get_backtest_history',
      symbol,
      limit
    });

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
    const result = JSON.parse(fullResponse);

    // Extract the text content
    const text = result.result?.content?.[0]?.text;
    if (!text) {
      return NextResponse.json({ records: [], count: 0 });
    }

    // Try to parse as JSON
    let historyData;
    try {
      historyData = JSON.parse(text);
    } catch {
      // Try extracting JSON from markdown code block
      const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonMatch) {
        historyData = JSON.parse(jsonMatch[1]);
      } else {
        historyData = { records: [], count: 0 };
      }
    }

    return NextResponse.json(historyData, {
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      },
    });
  } catch (error: any) {
    console.error('[backtest-history] Error:', error.message);
    return NextResponse.json(
      { records: [], count: 0, error: error.message },
      { status: 500 }
    );
  }
}
