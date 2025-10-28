#!/usr/bin/env python3
"""
cleanup_all.py - Complete System Cleanup
"""

import subprocess
import sys
from config import Config

def run_cmd(cmd, cwd=None):
    """Execute command"""
    print(f"🔄 {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"⚠️ Failed (ignored): {cmd}")
    else:
        print(f"✅ Completed: {cmd}")

def cleanup_step(name, commands):
    """Execute cleanup step"""
    print(f"\n🧹 {name}")
    for cmd, cwd in commands:
        run_cmd(cmd, cwd)

def main():
    print("🧹 AI Fund Manager System Cleanup")
    print(f"📍 Target Region: {Config.REGION}")
    
    response = input("Are you sure you want to delete all resources? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return 0
    
    # Cleanup steps (reverse order)
    steps = [
        ("Lab 4: Fund Manager", [
            ("python cleanup.py", "fund_manager")
        ]),
        ("Lab 3: Risk Manager", [
            ("python cleanup.py", "risk_manager")
        ]),
        ("Lab 2: Portfolio Architect", [
            ("python cleanup.py", "portfolio_architect")
        ]),
        ("Lab 1: Financial Analyst", [
            ("python cleanup.py", "financial_analyst")
        ])
    ]
    
    for name, commands in steps:
        cleanup_step(name, commands)
    
    print("\n🎉 Cleanup Complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())