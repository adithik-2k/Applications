import os
import sys
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.genai import types
from mcp import StdioServerParameters

load_dotenv()

# -----------------------------------
# System Instruction
# -----------------------------------
SYSTEM_INSTRUCTION = (
    "You are a GitHub profile analyst and dev card generator. "
    "When a user gives a GitHub username, ALWAYS do these steps in order: "
    "1. scrape_github "
    "2. analyze_profile "
    "3. generate_card_html "
    "4. save_card "
    "Never skip steps."
)

# -----------------------------------
# MCP Toolset
# -----------------------------------
mcp_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=[
            os.path.join(
                os.path.dirname(__file__),
                "mcp_server.py"
            )
        ],
    )
)

# -----------------------------------
# Agent
# -----------------------------------
github_card_agent = Agent(
    name="github_card_agent",

    # safer model for quota
    model="gemini-2.0-flash-lite",

    instruction=SYSTEM_INSTRUCTION,

    # pass toolset directly
    tools=[mcp_toolset],

    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=5,
                attempts=3
            )
        )
    )
)