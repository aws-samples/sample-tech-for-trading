import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentCore Trading Strategy Backtester",
  description: "Create and backtest trading strategies using Amazon Bedrock AgentCore",
};

import { BacktestProvider } from "@/lib/BacktestContext";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-dark-primary">
        <BacktestProvider>{children}</BacktestProvider>
      </body>
    </html>
  );
}
