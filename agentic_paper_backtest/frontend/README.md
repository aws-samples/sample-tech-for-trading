# AgentCore Paper Backtester Frontend

A Next.js application for uploading trading research papers (PDF) and backtesting the extracted strategy using Amazon Bedrock AgentCore.

## 🎯 Features

- **Paper Upload** - Drag & drop a research paper PDF; agents extract the trading idea
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

Copy `.env.example` to `.env.local` and fill in your values (all are read
server-side by Next.js API routes — never expose credentials with a
`NEXT_PUBLIC_` prefix):

```env
AWS_REGION=us-east-1
AGENTCORE_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/your-agent-runtime-id

# Cognito login (see DEPLOYMENT_GUIDE.md for user pool creation)
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_APP_CLIENT_ID=your-app-client-id
COGNITO_REGION=us-east-1
```

AWS credentials come from your local AWS profile / IAM role (e.g.
`AWS_PROFILE=default npm run dev`); do not put access keys in this file.

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
    "buy_conditions": "Price above 20-day moving average and RSI below 70",
    "sell_conditions": "Price below 20-day moving average or RSI above 80"
  }'
```

## 🚀 Deployment

### AWS S3 + CloudFront (Recommended)

Deploy as a static site to S3 with CloudFront CDN:

```bash
# 1. Configure environment variables
cp .env.example .env.local
# Edit .env.local with your AWS credentials

# 2. Deploy
./deploy.sh
```

The script will:
- ✅ Build Next.js as static export
- ✅ Create S3 bucket + CloudFront distribution
- ✅ Upload files with proper caching
- ✅ Invalidate CloudFront cache
- ✅ Give you the website URL

**First deployment:** Wait 5-10 minutes for CloudFront to deploy globally.

**Updates:** Just run `./deploy.sh` again - changes are live in 1-2 minutes.

**Cost:** ~$1-2/month for moderate usage (S3 + CloudFront)

**Important Notes:**
- Environment variables must be prefixed with `NEXT_PUBLIC_` for static export
- Variables are embedded at build time (rebuild to update)
- AWS credentials are in client-side code (consider Cognito for production)

### Alternative: Vercel

For server-side rendering (SSR) support:

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

Add environment variables in Vercel dashboard (without `NEXT_PUBLIC_` prefix).

### Alternative: AWS Amplify

1. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify/)
2. Connect your GitHub repository
3. Framework: Next.js SSR
4. Add environment variables
5. Deploy

## 🐛 Troubleshooting

### Development Issues

**"AgentCore ARN not configured"**
- Check `.env.local` has `AGENTCORE_ARN` set

**"Access denied"**
- Verify AWS credentials in `.env.local`
- Check IAM permissions include `bedrock-agentcore:InvokeAgentRuntime`

**"Module not found"**
- Run `npm install`

**"Port 3000 already in use"**
- Kill process: `lsof -ti:3000 | xargs kill -9`
- Or use different port: `npm run dev -- -p 3001`

**Double API Calls**
- This is React StrictMode in development (normal)
- Production builds only call once
- We use `useRef` to prevent duplicates

### Deployment Issues

**Build fails**
```bash
# Clear cache and rebuild
rm -rf .next out node_modules
npm install
npm run build
```

**CloudFront shows old content**
```bash
# Manually invalidate cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

**API calls fail after deployment**
- Check `NEXT_PUBLIC_` prefix on all environment variables
- Verify credentials are correct in `.env.local`
- Rebuild and redeploy after changing environment variables

**404 errors on page refresh**
- This is normal - CloudFormation template handles it
- Custom error responses redirect 404s to index.html

**Deployment script fails**
- Ensure AWS CLI is configured: `aws configure`
- Check IAM permissions for S3, CloudFront, CloudFormation
- Verify Node.js 18+ is installed

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

### Current Architecture (Static Export)

When deployed to S3 + CloudFront, the app uses **client-side AWS SDK**:

```
Browser → AWS SDK (with embedded credentials) → AgentCore Runtime
```

**How it works:**
- AWS credentials are embedded in JavaScript at build time (`NEXT_PUBLIC_*` variables)
- Browser directly calls AgentCore using AWS SDK for JavaScript v3
- No backend server needed

**Security considerations:**
- ⚠️ Credentials visible in browser source code
- ⚠️ All users share same credentials
- ⚠️ Can't rotate without rebuild
- ✅ Acceptable for development/demos
- ✅ Simple architecture, low cost

### Production Recommendations

For production deployments, consider these alternatives:

**Option 1: API Gateway + Lambda** (Most Secure)
```
Browser → API Gateway → Lambda (IAM role) → AgentCore
```
- ✅ No credentials in browser
- ✅ User authentication via Cognito
- ✅ Rate limiting and monitoring
- ⚠️ More complex setup
- ⚠️ Higher cost (~$5/month)

**Option 2: Cognito Identity Pool** (Balanced)
```
Browser → Cognito (temporary credentials) → AgentCore
```
- ✅ Temporary credentials
- ✅ User-specific access
- ✅ Simpler than API Gateway
- ✅ Low cost (~$1.50/month)

**Current approach is fine for:**
- Development and testing
- Internal demos
- Proof of concepts
- Low-risk applications

**Migrate to production architecture when:**
- Deploying to external users
- Need user authentication
- Require audit trails
- Security compliance needed

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
