# AgentCore Interactive Backtesting - Enhanced Edition

A modern, animated frontend application demonstrating AgentCore capabilities through an interactive trading strategy backtesting experience. Features dark theme with glass morphism effects, Three.js animations, and comprehensive educational workflow for AgentCore enablement sessions.

**Now with Enhanced Frontend Experience:**
- 🎨 Dark theme with glass morphism effects
- 🌟 Three.js animations and particle systems  
- 📚 Educational workflow for instructor-led sessions
- 🏗️ Interactive AgentCore architecture visualization
- 📊 Enhanced results display with animated charts

## 🏗️ Architecture Evolution

This project evolved from a complex multi-agent system to a **unified single-agent approach** demonstrating AgentCore best practices:

### **Final Architecture (Recommended)**
```
agentcore-enablement/
├── agent.py                    # 🎯 UNIFIED AGENT (replaces 5+ separate agents)
├── deploy_agent.sh             # Simple deployment script
├── requirements.txt            # Python dependencies
├── frontend/                   # React application
│   ├── src/components/         # React components
│   └── public/                 # Static assets
└── tools/                      # AgentCore Gateway demonstration
    ├── market-data-lambda/     # Lambda function for Gateway
    ├── deploy_market_data_tool.sh  # Deploy Lambda
    ├── setup_gateway.py        # Configure AgentCore Gateway
    └── deploy_tools.sh         # Complete Gateway setup
```

## 🚀 AgentCore Services Demonstrated

- **AgentCore Runtime**: Unified agent execution with tool orchestration
- **AgentCore Memory**: Workflow state and results persistence  
- **AgentCore Gateway**: External service integration via MCP protocol
- **AgentCore Identity**: User authentication and session management
- **Strands Framework**: Intelligent tool selection and chaining

## 🎨 Enhanced Frontend Features

### **Modern UI Design**
- **Dark Theme**: Professional dark color scheme with high contrast
- **Glass Morphism**: Transparent glass effects with backdrop blur and subtle borders
- **Responsive Layout**: Optimized for desktop, tablet, and mobile devices
- **Accessibility**: Keyboard navigation, screen reader support, reduced motion preferences

### **Three.js Animation System**
- **Scene-Specific Backgrounds**: Different 3D environments for each application section
- **Particle Systems**: Dynamic particle effects with configurable intensity
- **Performance Optimization**: Automatic quality adjustment based on device capabilities
- **Interactive Elements**: Floating geometric shapes and animated connections

### **Educational Workflow**
- **AgentCore Introduction**: Comprehensive overview of platform capabilities and architecture
- **Interactive Architecture**: Real-time highlighting of active AgentCore components
- **Step-by-Step Explanations**: Detailed information about each service during workflow execution
- **Instructor Controls**: Designed for guided enablement sessions and presentations

### **Enhanced Strategy Builder**
- **Stock Selection**: Dropdown with popular stocks (AAPL, MSFT, GOOGL, TSLA, etc.)
- **Smart Validation**: Real-time form validation with helpful error messages and suggestions
- **Example Conditions**: Quick-select buttons for common trading conditions
- **Live Preview**: Real-time strategy configuration preview with validation status

### **Animated Workflow Progress**
- **Architecture Visualization**: Interactive diagram showing AgentCore component relationships
- **Real-time Highlighting**: Visual indication of which services are currently processing
- **Educational Content**: Detailed explanations of each AgentCore service and its benefits
- **Progress Tracking**: Animated progress bars and completion indicators

### **Rich Results Display**
- **Performance Visualization**: Interactive charts showing portfolio performance over time
- **Animated Metrics**: Smooth number animations and visual performance indicators
- **Risk Analysis**: Comprehensive risk metrics including drawdown and Sharpe ratio
- **AgentCore Summary**: Detailed breakdown of which services were used and their processing times

## 🚀 Quick Start

### **Option 1: Unified Agent Only (Recommended)**
```bash
# Deploy the unified agent
./deploy_agent.sh

# Test both patterns
agentcore invoke '{"data_source": "auto", "initial_investment": 10000, "investment_area": "Technology", "buy_condition": "price above moving average", "sell_condition": "price below moving average"}' --agent unified_backtesting
```

### **Option 2: With AgentCore Gateway Demo**
```bash
# 1. Deploy Lambda function and configure Gateway
cd tools
./deploy_tools.sh

# 2. Deploy unified agent with Gateway environment variables
cd ..
export AGENTCORE_GATEWAY_MCP_URL="your-gateway-url"
export AGENTCORE_GATEWAY_TOKEN="your-oauth-token"
./deploy_agent.sh

# 3. Test Gateway pattern specifically
agentcore invoke '{"data_source": "gateway", "initial_investment": 5000, "investment_area": "Healthcare", "buy_condition": "uptrend", "sell_condition": "downtrend"}' --agent unified_backtesting
```

### **Option 3: Enhanced Frontend Experience (Recommended for Demos)**
```bash
# Install and run enhanced frontend
cd frontend
npm install

# Configure environment (optional)
cp .env.example .env
# Edit .env with your AgentCore configuration

# Start development server
npm start
# Open http://localhost:3000

# Or deploy to AWS S3/CloudFront
npm run build
./deploy_frontend.sh
```

**Enhanced Frontend Features:**
- 🎯 **AgentCore Introduction**: Comprehensive platform overview with architecture diagrams
- 🎨 **Glass Morphism UI**: Modern dark theme with transparent glass effects
- 🌟 **Three.js Animations**: Dynamic 3D backgrounds and particle systems
- 📈 **Enhanced Strategy Builder**: Stock dropdown, real-time validation, example conditions
- 🔄 **Animated Workflow**: Real-time AgentCore component highlighting during execution
- 📊 **Rich Results Display**: Interactive charts, performance categorization, animated metrics
- 🎓 **Educational Content**: Step-by-step explanations of each AgentCore service

## 🧪 Testing Different Patterns

### **Test Agent as Tool Pattern**
```bash
# Requires MARKET_DATA_AGENT_ARN environment variable
agentcore invoke '{"data_source": "agent", "initial_investment": 10000, "investment_area": "Technology", "buy_condition": "price above moving average", "sell_condition": "price below moving average"}' --agent unified_backtesting
```

### **Test AgentCore Gateway Pattern**
```bash
# Requires Gateway setup via tools/deploy_tools.sh
agentcore invoke '{"data_source": "gateway", "initial_investment": 7500, "investment_area": "Finance", "buy_condition": "rising trend", "sell_condition": "falling trend"}' --agent unified_backtesting
```

### **Test Auto Pattern Selection**
```bash
# Tries both patterns automatically with fallback
agentcore invoke '{"initial_investment": 10000, "investment_area": "Technology", "buy_condition": "price above moving average", "sell_condition": "price below moving average"}' --agent unified_backtesting
```

## 📊 Implementation Status

✅ **Enhanced Frontend**: Modern UI with glass morphism and Three.js animations  
✅ **Educational Workflow**: Step-by-step AgentCore service demonstrations  
✅ **Interactive Architecture**: Real-time component highlighting and explanations  
✅ **Advanced Strategy Builder**: Stock selection, validation, and examples  
✅ **Animated Results**: Performance visualization with interactive charts  
✅ **Unified Agent**: Single agent with 6 specialized tools  
✅ **AgentCore Gateway**: Lambda function and MCP configuration  
✅ **Pattern Demonstrations**: Both "Agent as Tool" patterns implemented  
✅ **Instructor Ready**: Designed for enablement sessions and presentations  

## 🎓 Key Learning: Agent as Tool Patterns in AgentCore

### **Understanding the Patterns**

#### **1. Agent as Tool (Agent-to-Agent)**
```python
# In Strands agent
@tool
def invoke_market_data_agent(investment_area: str):
    # Call another deployed AgentCore agent
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=market_data_agent_arn,
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps({'investment_area': investment_area}).encode()
    )
    return process_response(response)
```

**When to Use:**
- ✅ Reusing existing specialized agents across workflows
- ✅ Maintaining separation of concerns with dedicated agents
- ✅ Building agent ecosystems with inter-agent communication
- ❌ Simple workflows (adds complexity and latency)

#### **2. AgentCore Gateway (External Service as Tool)**
```python
# In Strands agent
@tool
def fetch_market_data_via_gateway(investment_area: str):
    # Call external service via AgentCore Gateway MCP
    async with httpx.AsyncClient() as client:
        response = await client.post(
            gateway_url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "fetch_market_data",
                    "arguments": {"investment_area": investment_area}
                }
            }
        )
```

**When to Use:**
- ✅ Integrating external APIs, databases, or services
- ✅ Exposing Lambda functions as agent tools
- ✅ Standardizing external service access via MCP protocol
- ✅ OAuth-secured external service integration

### **Architecture Decision Framework**

| Scenario | Recommended Pattern | Reasoning |
|----------|-------------------|-----------|
| **Simple workflow** | Unified agent with `@tool` functions | Minimal complexity, fast execution |
| **Reusing existing agents** | Agent as Tool | Leverage existing investments |
| **External API integration** | AgentCore Gateway | Standardized, secure access |
| **Complex multi-step workflows** | Unified agent with tool chaining | Better orchestration, easier debugging |
| **Microservices architecture** | Agent as Tool | Service separation, independent scaling |

### **Performance Considerations**

- **Unified Agent**: Fastest (no network calls between tools)
- **Agent as Tool**: Medium (network latency between agents)
- **AgentCore Gateway**: Variable (depends on external service performance)

### **Deployment Complexity**

- **Unified Agent**: 1 deployment, 1 configuration
- **Agent as Tool**: N deployments, ARN management, environment variables
- **AgentCore Gateway**: Lambda + Gateway + OAuth setup

## 🔧 Development Evolution Notes

### **What We Learned**
1. **Start Simple**: Begin with unified agents, add complexity only when needed
2. **Pattern Selection**: Choose based on actual requirements, not theoretical benefits
3. **AgentCore Gateway**: Excellent for external service integration
4. **Strands Power**: Intelligent tool orchestration reduces manual workflow coding
5. **Minimal Architecture**: 1 agent with 6 tools > 5 agents with complex orchestration

### **Best Practices Discovered**
- Use environment variables for pattern switching (`data_source` parameter)
- Implement fallback mechanisms for robust operation
- Separate Gateway setup from agent deployment for flexibility
- Document both patterns for educational purposes
- Keep tool functions focused and single-purpose

## 🧹 Cleanup

```bash
# Delete unified agent
agentcore destroy --agent unified_backtesting --force

# Delete Gateway resources (if deployed)
cd tools
aws lambda delete-function --function-name market-data-fetcher
aws iam delete-role --role-name MarketDataLambdaRole

# Delete frontend resources (if deployed)
aws s3 rm s3://your-bucket-name --recursive
aws cloudformation delete-stack --stack-name backtesting-frontend
```
## 🏗
️ Technical Architecture

### **Frontend Structure**
```
frontend/src/
├── components/
│   ├── ui/                     # Reusable glass morphism components
│   │   ├── GlassCard.tsx       # Glass effect card component
│   │   ├── GlassInput.tsx      # Glass-themed form inputs
│   │   ├── GlassSelect.tsx     # Glass-themed dropdown
│   │   ├── AnimatedButton.tsx  # Animated button with hover effects
│   │   └── LoadingSpinner.tsx  # Three.js animated loader
│   ├── animations/             # Three.js and animation components
│   │   ├── ThreeBackground.tsx # Scene-specific 3D backgrounds
│   │   ├── ParticleSystem.tsx  # Particle effects system
│   │   └── ComponentHighlight.tsx # Architecture highlighting
│   ├── IntroductionPage.tsx    # Enhanced AgentCore introduction
│   ├── StrategyBuilder.tsx     # Enhanced strategy form
│   ├── ProgressVisualization.tsx # Animated workflow progress
│   └── ResultsDisplay.tsx      # Enhanced results with charts
├── hooks/
│   ├── useWorkflowState.ts     # Workflow state management
│   ├── useAnimations.ts        # Animation performance optimization
│   └── useGlassTheme.ts        # Glass morphism theme management
├── services/
│   ├── simulationService.ts    # Realistic backtesting simulation
│   └── api.ts                  # AgentCore API integration
├── types/
│   ├── workflow.ts             # Workflow and AgentCore types
│   ├── strategy.ts             # Trading strategy types
│   └── agentcore.ts            # AgentCore service definitions
└── styles/
    ├── globals.css             # Global dark theme styles
    └── glass-morphism.css      # Glass effect utilities
```

### **Design Decisions**

#### **Glass Morphism Implementation**
- **CSS Variables**: Centralized theme management with CSS custom properties
- **Backdrop Filter**: Hardware-accelerated blur effects with fallbacks for unsupported browsers
- **Component System**: Reusable glass components with configurable blur, opacity, and glow effects
- **Performance**: Optimized for 60fps animations with automatic quality adjustment

#### **Three.js Integration**
- **React Three Fiber**: Declarative Three.js integration with React component lifecycle
- **Scene Management**: Different 3D environments for intro, builder, workflow, and results pages
- **Performance Monitoring**: Automatic frame rate detection and quality adjustment
- **Memory Management**: Proper cleanup of Three.js objects to prevent memory leaks

#### **State Management**
- **Custom Hooks**: Specialized hooks for workflow state, animations, and theme management
- **Educational Content**: Structured data for AgentCore service explanations and benefits
- **Simulation Service**: Realistic backtesting engine with configurable market conditions
- **API Integration**: Ready for real AgentCore backend with fallback to simulation

#### **Animation System**
- **Framer Motion**: Smooth page transitions and micro-interactions
- **Performance Optimization**: Respects user's reduced motion preferences
- **Progressive Enhancement**: Graceful degradation for lower-performance devices
- **Accessibility**: Full keyboard navigation and screen reader support

### **Environment Configuration**

#### **Development Environment**
```env
# AgentCore Integration
REACT_APP_AGENTCORE_API_URL=http://localhost:8000
REACT_APP_AGENTCORE_GATEWAY_URL=http://localhost:8001
REACT_APP_MOCK_API=true

# Performance Settings
REACT_APP_ENABLE_THREE_JS=true
REACT_APP_ENABLE_ANIMATIONS=true
REACT_APP_PERFORMANCE_MODE=auto

# Development Features
REACT_APP_DEBUG_MODE=true
REACT_APP_SHOW_PERFORMANCE_METRICS=true
```

#### **Production Environment**
```env
# AgentCore Integration
REACT_APP_AGENTCORE_API_URL=https://your-agentcore-api.amazonaws.com
REACT_APP_AGENTCORE_GATEWAY_URL=https://your-gateway-url.amazonaws.com
REACT_APP_AGENTCORE_GATEWAY_TOKEN=your-oauth-token
REACT_APP_MOCK_API=false

# Performance Settings
REACT_APP_ENABLE_THREE_JS=true
REACT_APP_ENABLE_ANIMATIONS=true
REACT_APP_PERFORMANCE_MODE=auto

# Production Features
REACT_APP_DEBUG_MODE=false
REACT_APP_ANALYTICS_ID=your-analytics-id
```

### **Performance Optimizations**

#### **Three.js Performance**
- **Automatic Quality Adjustment**: Monitors frame rate and adjusts particle count and effects
- **Level of Detail (LOD)**: Reduces animation complexity on lower-end devices
- **Memory Management**: Proper disposal of geometries, materials, and textures
- **Lazy Loading**: Animation assets loaded only when needed

#### **React Performance**
- **Code Splitting**: Route-based code splitting with React.lazy()
- **Memoization**: Strategic use of React.memo, useMemo, and useCallback
- **Virtual Scrolling**: For large datasets in results visualization
- **Debounced Inputs**: Prevents excessive re-renders during form input

#### **CSS Performance**
- **Hardware Acceleration**: Uses transform3d for GPU-accelerated animations
- **Critical CSS**: Inlines critical styles for faster initial render
- **CSS-in-JS Optimization**: Tailwind CSS with purging for minimal bundle size
- **Backdrop Filter Fallbacks**: Graceful degradation for unsupported browsers

### **Browser Compatibility**

#### **Supported Browsers**
- **Chrome**: 90+ (full feature support)
- **Firefox**: 88+ (full feature support)
- **Safari**: 14+ (full feature support)
- **Edge**: 90+ (full feature support)

#### **Required Features**
- **WebGL**: Required for Three.js animations
- **Backdrop Filter**: Required for glass morphism effects (with fallbacks)
- **CSS Grid**: Required for responsive layouts
- **ES2020**: Required for modern JavaScript features

#### **Graceful Degradation**
- **No WebGL**: Falls back to CSS animations only
- **No Backdrop Filter**: Uses solid backgrounds with transparency
- **Reduced Motion**: Respects user preferences and disables animations
- **Low Performance**: Automatically reduces animation quality

### **Deployment Architecture**

#### **AWS S3 + CloudFront**
```bash
# Build and deploy pipeline
npm run build                    # Create production build
aws s3 sync build/ s3://bucket   # Upload to S3
aws cloudfront create-invalidation # Clear CDN cache
```

#### **Environment-Specific Builds**
- **Development**: Source maps, debug mode, mock API
- **Staging**: Minified code, real API, performance monitoring
- **Production**: Optimized build, analytics, error reporting

### **Testing Strategy**

#### **Unit Tests**
- **Component Testing**: React Testing Library for component behavior
- **Hook Testing**: Custom hooks with @testing-library/react-hooks
- **Utility Testing**: Pure functions and service layer testing
- **Animation Testing**: Mock Three.js for consistent test environments

#### **Integration Tests**
- **Workflow Testing**: End-to-end workflow state management
- **API Integration**: Mock AgentCore API responses
- **Performance Testing**: Animation frame rate and memory usage
- **Accessibility Testing**: Keyboard navigation and screen reader support

#### **Visual Regression Tests**
- **Glass Morphism**: Consistent styling across browsers
- **Animation Consistency**: Smooth transitions and effects
- **Responsive Design**: Layout testing across device sizes
- **Dark Theme**: Color contrast and readability validation

## 🎓 Educational Use Cases

### **For AgentCore Enablement Sessions**

#### **Instructor Guide**
1. **Introduction Phase** (5-10 minutes)
   - Present AgentCore Identity overview and architecture
   - Explain the four key identity capabilities
   - Show the interactive architecture diagram

2. **Strategy Building Phase** (10-15 minutes)
   - Guide participants through the enhanced strategy builder
   - Demonstrate stock selection and condition examples
   - Show real-time validation and preview features

3. **Workflow Demonstration Phase** (15-20 minutes)
   - Start the backtesting workflow
   - Explain each AgentCore service as it becomes active
   - Highlight the architecture components in real-time
   - Discuss the benefits and use cases of each service

4. **Results Analysis Phase** (10-15 minutes)
   - Review the animated performance metrics
   - Explain the risk analysis and trading statistics
   - Summarize the AgentCore services that were demonstrated
   - Discuss real-world applications and next steps

#### **Participant Experience**
- **Interactive Learning**: Hands-on experience with AgentCore concepts
- **Visual Understanding**: See how AgentCore components work together
- **Practical Application**: Create and test actual trading strategies
- **Comprehensive Results**: Understand performance metrics and analysis

### **For Development Teams**

#### **Architecture Patterns**
- **Glass Morphism Design System**: Reusable component library
- **Three.js Integration**: Performance-optimized 3D graphics
- **Educational Workflow**: Step-by-step user guidance patterns
- **Animation Performance**: Frame rate monitoring and optimization

#### **AgentCore Integration**
- **Service Demonstration**: Real-world examples of each AgentCore service
- **API Integration**: Ready-to-use patterns for AgentCore backend integration
- **Error Handling**: Graceful fallbacks and user-friendly error messages
- **Performance Monitoring**: Built-in metrics and optimization strategies

---

**Enhanced Frontend Implementation Complete** ✨

This enhanced version transforms the original backtesting application into a modern, educational experience perfect for AgentCore enablement sessions and demonstrations. The combination of beautiful UI design, smooth animations, and comprehensive educational content creates an engaging way to learn about AgentCore's capabilities.