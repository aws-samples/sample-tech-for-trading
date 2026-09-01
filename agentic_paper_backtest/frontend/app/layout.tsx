import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentCore Paper Backtester",
  description: "Upload a trading research paper and backtest its strategy using Amazon Bedrock AgentCore",
};

import { BacktestProvider } from "@/lib/BacktestContext";
import UsageTrackerInit from "@/components/UsageTrackerInit";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-dark-primary">
        <Script src="/usage-tracker-config.js" strategy="beforeInteractive" />
        <Script src="/usage-tracker-auto.bundle.min.js" strategy="beforeInteractive" />
        <UsageTrackerInit />
        <BacktestProvider>{children}</BacktestProvider>
      </body>
    </html>
  );
}
