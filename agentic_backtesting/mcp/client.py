"""
MCP Client for Redshift integration with fallback to direct connection
"""

import json
import os
import psycopg2
import pandas as pd
from typing import Dict, Any, List
from dotenv import load_dotenv

class RedshiftMCPClient:
    """Client for interacting with Redshift via MCP or direct connection"""
    
    def __init__(self, config_path: str = "mcp/config.json"):
        load_dotenv()  # Load environment variables
        self.config_path = config_path
        self.connection = self._init_direct_connection()
    
    def _init_direct_connection(self):
        """Initialize direct Redshift connection as fallback"""
        try:
            return psycopg2.connect(
                host=os.getenv('PGHOST'),
                port=int(os.getenv('PGPORT', 5439)),
                user=os.getenv('PGUSER'),
                password=os.getenv('PGPASSWORD'),
                database=os.getenv('PGDATABASE')
            )
        except Exception as e:
            print(f"❌ Direct connection failed: {e}")
            return None
    
    def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool using direct database connection"""
        try:
            if tool_name == "execute_query" and self.connection:
                query = parameters.get("query", "")
                df = pd.read_sql_query(query, self.connection)
                return {
                    "data": df.to_dict('records'),
                    "columns": df.columns.tolist(),
                    "status": "success"
                }
            return {"error": "Tool not supported or no connection"}
        except Exception as e:
            return {"error": str(e)}
    
    def list_tools(self) -> List[str]:
        """List available tools"""
        return ["execute_query", "describe_table", "list_tables"]
