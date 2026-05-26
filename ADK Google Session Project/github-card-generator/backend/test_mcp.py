import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_test():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("Step 1: Scraping github for 'torvalds'...")
            github_data = await session.call_tool("scrape_github", arguments={"username": "torvalds"})
            
            # MCP Tool calls return a list of content blocks
            data = json.loads(github_data.content[0].text)
            if "error" in data:
                print(f"Scrape Error: {data['error']}")
                return

            print("Step 2: Analyzing profile...")
            try:
                analysis = await session.call_tool("analyze_profile", arguments={"github_data": data})
                if not analysis.content:
                    print("Error: No content returned from analyze_profile")
                    return
                print(f"DEBUG: Analysis Raw Response: {analysis.content[0].text}")
                analysis_data = json.loads(analysis.content[0].text)
            except Exception as e:
                print(f"Error in Step 2: {e}")
                # Try to see if there was a tool error message
                return
            
            print("Step 3: Generating card HTML...")
            card_html = await session.call_tool("generate_card_html", arguments={
                "username": "torvalds", 
                "github_data": data, 
                "analysis": analysis_data
            })
            
            print("\n--- RESULTS ---")
            print(f"Card Theme: {analysis_data.get('card_theme')}")
            print(f"Developer Vibe: {analysis_data.get('developer_vibe')}")
            print("----------------")

if __name__ == '__main__':
    asyncio.run(run_test())
