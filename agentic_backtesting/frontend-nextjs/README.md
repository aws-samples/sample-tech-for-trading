# AgentCore Trading Strategy Backtester

A modern Next.js application for creating and backtesting trading strategies using Amazon Bedrock AgentCore.

## 🎯 Features

- **Strategy Builder** - Create custom trading strategies with visual form
- **AgentCore Integration** - Direct AWS SDK integration via Next.js API routes
- **Real-time Workflow** - Animated progress visualization
- **AI Analysis** - Get detailed performance analysis from AgentCore
- **Glass-morphism UI** - Beautiful, modern interface
- **TypeScript** - Full type safety throughout

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- AWS Account with AgentCore access
- AWS credentials configured

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env.local` and add your credentials:

```env
AWS_REGION=us-east-1
AGENTCORE_ARN=arn:aws:bedrock-agentcore:us-east-1:600627331406:runtime/quant_agent-D6li6lBv47
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
NEXT_PUBLIC_USE_MOCK_DATA=false
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## 📁 Project Structure

```
frontend-nextjs/
├── app/
│   ├── api/execute-backtest/route.ts  # AgentCore API route
│   ├── workflow/page.tsx              # Workflow animation
│   ├── results/page.tsx               # Results display
│   ├── page.tsx                       # Strategy builder (home)
│   ├── layout.tsx                     # Root layout
│   └── globals.css                    # Global styles
├── components/ui/                     # Reusable UI components
├── lib/
│   ├── agentcore-api.ts              # API client
│   └── BacktestContext.tsx           # React Context for state
├── types/strategy.ts                  # TypeScript types
├── .env.local                         # Environment variables
└── deploy.sh                          # Deployment script
```

## 🏗️ Architecture

```
Next.js App (localhost:3000)
├── Frontend (React)
│   └── Strategy Builder, Workflow, Results
└── API Routes (Built-in)
    └── /api/execute-backtest
        └── AWS SDK → AgentCore Runtime
```

**Key Advantage**: No separate backend needed! Next.js API routes handle everything.

## 🔧 How It Works

### 1. User Flow

1. **Home** - Fill out strategy form
2. **Workflow** - Watch animated progress (API call happens here)
3. **Results** - See backtest results instantly (from React Context)

### 2. API Integration

**API Route** (`app/api/execute-backtest/route.ts`):
- Receives strategy input
- Invokes AgentCore using AWS SDK
- Returns analysis to frontend

**React Context** (`lib/BacktestContext.tsx`):
- Stores API result globally
- Shares data between workflow and results pages
- Prevents duplicate API calls

### 3. Data Flow

```
User submits strategy
    ↓
Workflow page starts API call
    ↓
Animation plays while API processes
    ↓
Result stored in React Context
    ↓
Navigate to results page
    ↓
Results page reads from Context (instant!)
```

## 🧪 Testing

### Test with Mock Data

```bash
# In .env.local
NEXT_PUBLIC_USE_MOCK_DATA=true

npm run dev
```

### Test with Real AgentCore

```bash
# In .env.local
NEXT_PUBLIC_USE_MOCK_DATA=false

npm run dev
```

### Test API Route Directly

```bash
# Health check
curl http://localhost:3000/api/execute-backtest

# Execute backtest
curl -X POST http://localhost:3000/api/execute-backtest \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Strategy",
    "stock_symbol": "AAPL",
    "backtest_window": "1Y",
    "max_positions": 1,
    "stop_loss": 5,
    "take_profit": 10,
    "buy_conditions": "EMA50 > EMA200",
    "sell_conditions": "EMA50 < EMA200"
  }'
```

## 🚀 Deployment

### Option 1: Vercel (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
./deploy.sh
# Choose option 1

# Or manually
vercel --prod
```

**Environment Variables in Vercel:**
- `AWS_REGION`
- `AGENTCORE_ARN`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### Option 2: AWS Amplify

```bash
./deploy.sh
# Choose option 2
# Follow the instructions
```

Or manually:
1. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify/)
2. Connect your GitHub repository
3. Framework: Next.js SSR
4. Add environment variables
5. Deploy

## 🐛 Troubleshooting

### "AgentCore ARN not configured"
- Check `.env.local` has `AGENTCORE_ARN` set

### "Access denied"
- Verify AWS credentials in `.env.local`
- Check IAM permissions include `bedrock-agentcore:InvokeAgentRuntime`

### "Module not found"
- Run `npm install`

### "Port 3000 already in use"
- Kill process: `lsof -ti:3000 | xargs kill -9`
- Or use different port: `npm run dev -- -p 3001`

### Double API Calls
- This is React StrictMode in development (normal)
- Production builds only call once
- We use `useRef` to prevent duplicates

### Logs

**Terminal logs** show AgentCore API calls:
```
========================================
[AgentCore] PROMPT:
========================================
how is the strategy performance: {...}
========================================

========================================
[AgentCore] RESPONSE:
========================================
## Strategy Performance Analysis...
========================================
```

**Browser console** shows workflow:
```
[Workflow] Starting API call...
[Workflow] ✅ API call complete, result stored in context
[Results] ✅ Using result from context (no API call)
```

## 📊 Performance

- **Single API call** - No duplicates
- **Parallel execution** - Animation runs during API processing
- **Instant results** - Results page reads from context
- **No timeout** - AgentCore can take as long as needed

## 🔐 Security

- **Server-side only** - AWS credentials never exposed to browser
- **Environment variables** - Sensitive data in `.env.local`
- **IAM roles** - Use IAM roles in production (no access keys)
- **HTTPS** - Always use HTTPS in production

## 📝 Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `AWS_REGION` | AWS region | Yes | `us-east-1` |
| `AGENTCORE_ARN` | AgentCore agent ARN | Yes | `arn:aws:bedrock-agentcore:...` |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes* | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes* | `...` |
| `NEXT_PUBLIC_USE_MOCK_DATA` | Use mock data | No | `false` |

*Use IAM roles in production instead of access keys

## 🎨 Customization

### Change Theme Colors

Edit `tailwind.config.ts`:
```typescript
colors: {
  'accent-blue': '#00d4ff',  // Change this
  'accent-purple': '#8b5cf6', // And this
  // ...
}
```

### Add New Stock Symbols

Edit `types/strategy.ts`:
```typescript
export const AVAILABLE_STOCKS: StockOption[] = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  // Add more here
];
```

### Modify Workflow Steps

Edit `app/workflow/page.tsx`:
```typescript
const workflowSteps: WorkflowStep[] = [
  // Modify or add steps here
];
```

## 📚 Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Framer Motion** - Animations
- **AWS SDK v3** - AgentCore integration
- **React Context** - State management

## 🤝 Why Next.js?

Compared to the original React + Flask setup:

| Feature | React + Flask | Next.js |
|---------|--------------|---------|
| Servers | 2 | 1 |
| Languages | JS + Python | JS only |
| CORS | Required | Not needed |
| Deployment | 2 separate | 1 unified |
| API Routes | Flask | Built-in |
| Complexity | Higher | Lower |

## 📖 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [AWS SDK for JavaScript](https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/)
- [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Framer Motion](https://www.framer.com/motion/)

## 🎉 Success Checklist

When everything works, you should see:

- ✅ Home page loads at http://localhost:3000
- ✅ Form validation works
- ✅ Clicking "Run Backtest" navigates to workflow
- ✅ Workflow animation plays (~15 seconds)
- ✅ Terminal shows single API call (PROMPT → RESPONSE)
- ✅ Results page loads instantly
- ✅ Performance metrics displayed
- ✅ AI analysis shown
- ✅ No errors in console

## 💡 Tips

- Use mock mode during development to save AWS costs
- Check terminal logs for AgentCore API details
- Use browser console to debug React issues
- Deploy to Vercel for easiest deployment
- Use IAM roles in production (not access keys)

## 📄 License

MIT

---

**Built with ❤️ using Next.js and Amazon Bedrock AgentCore**
