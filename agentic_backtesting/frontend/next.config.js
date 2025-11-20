/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  
  // Disable strict mode for better compatibility
  reactStrictMode: false,
  
  // Enable experimental features if needed
  experimental: {
    // Add any experimental features here if needed
  },
  
  // Environment variables that should be available at build time
  env: {
    AGENTCORE_ARN: process.env.AGENTCORE_ARN,
    AWS_REGION: process.env.AWS_REGION,
  },
}

module.exports = nextConfig