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
                query_param = parameters.get("query", "")
                
                # Check if query_param is an AgentResult object
                if hasattr(query_param, 'message') and hasattr(query_param.message, 'get'):
                    # Extract SQL from AgentResult
                    content = query_param.message.get('content', [])
                    if content and isinstance(content, list) and len(content) > 0:
                        text_content = content[0].get('text', '')
                        # Extract SQL from markdown code block
                        if '```sql' in text_content:
                            sql_start = text_content.find('```sql') + 6
                            sql_end = text_content.find('```', sql_start)
                            query = text_content[sql_start:sql_end].strip()
                        else:
                            query = text_content.strip()
                    else:
                        query = str(query_param)
                else:
                    # Use query directly as string
                    query = str(query_param)
                
                # Clean up SQL query - fix reserved keywords and formatting
                query = self._clean_sql_query(query)
                
                df = pd.read_sql_query(query, self.connection)
                return {
                    "data": df.to_dict('records'),
                    "columns": df.columns.tolist(),
                    "status": "success"
                }
            return {"error": "Tool not supported or no connection"}
        except Exception as e:
            return {"error": str(e)}
    
    def _clean_sql_query(self, query: str) -> str:
        """Clean and fix SQL query for PostgreSQL/Redshift"""
        # Remove extra whitespace and newlines
        query = ' '.join(query.split())
        
        # Fix reserved keywords by adding quotes
        reserved_keywords = ['open', 'close', 'date', 'timestamp', 'high', 'low', 'volume']
        for keyword in reserved_keywords:
            # Replace unquoted column names with quoted ones
            query = query.replace(f' {keyword} ', f' "{keyword}" ')
            query = query.replace(f' {keyword},', f' "{keyword}",')
            query = query.replace(f'({keyword} ', f'("{keyword}" ')
            query = query.replace(f'({keyword},', f'("{keyword}",')
        
        return query
    
    def list_tools(self) -> List[str]:
        """List available tools"""
        return ["execute_query", "describe_table", "list_tables"]
