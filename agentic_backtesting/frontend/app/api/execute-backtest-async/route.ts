import { NextRequest, NextResponse } from 'next/server';
import { BedrockAgentCoreClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agentcore';
import { v4 as uuidv4 } from 'uuid';

const AGENT_ARN = process.env.AGENTCORE_ARN!;

// In-memory store with persistence across hot reloads (use Redis/DynamoDB in production)
const results = new Map<string, any>();

// Add some basic persistence for development
if (typeof global !== 'undefined') {
  // @ts-ignore
  global.backtestResults = global.backtestResults || new Map();
  // @ts-ignore
  const persistedResults = global.backtestResults;

  // Restore results from global
  for (const [key, value] of persistedResults) {
    results.set(key, value);
  }
}

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
  const initialStatus = { status: 'processing', startTime: Date.now() };
  results.set(jobId, initialStatus);

  // Persist to global for hot reload survival
  if (typeof global !== 'undefined') {
    // @ts-ignore
    global.backtestResults = global.backtestResults || new Map();
    // @ts-ignore
    global.backtestResults.set(jobId, initialStatus);
  }

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
    const strategyCode = result.strategy_code || null;
    const trades = result.trades || [];
    const tradeSummary = result.trade_summary || {};
    const backtestMetrics = result.backtest_metrics || null;

    console.log('========================================');
    console.log('[AgentCore] EXTRACTED TEXT:');
    console.log('========================================');
    console.log(analysisText);
    console.log('========================================');
    if (strategyCode) {
      console.log('[AgentCore] Strategy code received (' + strategyCode.length + ' chars)');
    }
    console.log(`[AgentCore] Trades received: ${trades.length}`);
    if (backtestMetrics) {
      console.log('[AgentCore] Backtest metrics received:', JSON.stringify(backtestMetrics));
    }

    const completeResult = {
      status: 'complete',
      data: {
        success: true,
        analysis: analysisText,
        strategyInput,
        strategyCode,
        trades,
        trade_summary: tradeSummary,
        backtest_metrics: backtestMetrics
      }
    };

    console.log(`[API] 💾 Setting complete result for job ${jobId}:`, JSON.stringify(completeResult, null, 2));
    results.set(jobId, completeResult);
    console.log(`[API] ✅ Job ${jobId} marked as complete in results map`);

    // Persist to global FIRST, then local
    if (typeof global !== 'undefined') {
      // @ts-ignore
      global.backtestResults = global.backtestResults || new Map();
      // @ts-ignore
      global.backtestResults.set(jobId, completeResult);
      console.log(`[API] ✅ Job ${jobId} persisted to global storage`);
    }

    // Double-check that the result was actually set
    const verifyResult = results.get(jobId);
    console.log(`[API] 🔍 Verification - Job ${jobId} status in map:`, verifyResult?.status);

    console.log(`[API] 🎉 processBacktest completed successfully for job ${jobId}`);
  } catch (error: any) {
    console.log('========================================');
    console.log('[AgentCore] ERROR:');
    console.log('========================================');
    console.log('Error message:', error.message);
    console.log('Error stack:', error.stack);
    console.log('========================================');

    const errorResult = {
      status: 'error',
      error: error.message
    };

    console.log(`[API] ❌ Setting error result for job ${jobId}:`, errorResult);
    results.set(jobId, errorResult);

    // Persist to global
    if (typeof global !== 'undefined') {
      // @ts-ignore
      global.backtestResults = global.backtestResults || new Map();
      // @ts-ignore
      global.backtestResults.set(jobId, errorResult);
    }

    console.log(`[API] 💥 processBacktest failed for job ${jobId}`);
  }
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const jobId = url.searchParams.get('jobId');

  if (!jobId) {
    return NextResponse.json({ error: 'jobId required' }, { status: 400 });
  }

  // Always check global first (most up-to-date after hot reloads), then local
  console.log(`[API] 🔍 GET request for job ${jobId}`);
  let result;

  // @ts-ignore
  if (typeof global !== 'undefined' && global.backtestResults) {
    // @ts-ignore
    result = global.backtestResults.get(jobId);
    console.log(`[API] 📋 Global result for job ${jobId}:`, result?.status || 'NOT_FOUND');
    if (result) {
      // Sync to local map
      results.set(jobId, result);
    }
  }

  // Fallback to local if not in global
  if (!result) {
    result = results.get(jobId);
    console.log(`[API] 📋 Local result for job ${jobId}:`, result?.status || 'NOT_FOUND');
  }

  if (!result) {
    console.log(`[API] Job ${jobId} not found. Available jobs:`, Array.from(results.keys()));
    return NextResponse.json({
      error: 'Job not found. It may have expired or the server restarted.',
      jobId,
      availableJobs: Array.from(results.keys()).length
    }, { status: 404 });
  }

  console.log(`[API] 📤 Returning result for job ${jobId}:`, JSON.stringify(result, null, 2));
  return NextResponse.json(result, {
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate',
    },
  });
}
