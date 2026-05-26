import os
import httpx
import json
from collections import Counter
from mcp.server.fastmcp import FastMCP
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

mcp = FastMCP("GitHub-Card-Generator")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_ID = "gemini-2.0-flash" # Gemini 2.5 Flash confirmed available.

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """Fetch user profile information and top repositories from GitHub."""
    headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"} if os.getenv("GITHUB_TOKEN") else {}
    async with httpx.AsyncClient(headers=headers) as http_client:
        # Fetch user profile
        user_res = await http_client.get(f"https://api.github.com/users/{username}")
        if user_res.status_code != 200:
            return {"error": f"User {username} not found"}
        user_data = user_res.json()

        # Fetch repositories
        repos_res = await http_client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100")
        repos_data = repos_res.json()

        # Aggregate languages
        languages = Counter()
        top_repos = []
        
        # Sort by stars and take top 6
        sorted_repos = sorted(repos_data, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
        
        for repo in sorted_repos:
            top_repos.append({
                "name": repo.get("name"),
                "stars": repo.get("stargazers_count"),
                "language": repo.get("language"),
                "description": repo.get("description")
            })

        for repo in repos_data:
            lang = repo.get("language")
            if lang:
                languages[lang] += 1

        return {
            "name": user_data.get("name"),
            "bio": user_data.get("bio"),
            "location": user_data.get("location"),
            "avatar_url": user_data.get("avatar_url"),
            "public_repos": user_data.get("public_repos"),
            "followers": user_data.get("followers"),
            "top_repos": top_repos,
            "most_used_languages": dict(languages.most_common(5))
        }

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """Use Gemini to analyze the GitHub profile and determine the developer vibe."""
    prompt = f"""
    Analyze this GitHub profile data and return a JSON object with:
    - developer_vibe (1 sentence personality)
    - top_skills (list of 3)
    - fun_fact (something clever inferred from their repos)
    - card_theme (one of: "hacker", "builder", "researcher", "designer", "open-source-hero")

    Profile Data:
    {json.dumps(github_data, indent=2)}
    """
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "developer_vibe": {"type": "STRING"},
                    "top_skills": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "fun_fact": {"type": "STRING"},
                    "card_theme": {"type": "STRING", "enum": ["hacker", "builder", "researcher", "designer", "open-source-hero"]}
                },
                "required": ["developer_vibe", "top_skills", "fun_fact", "card_theme"]
            }
        )
    )
    return json.loads(response.text)

@mcp.tool()
async def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generate a self-contained HTML string for a beautiful dev card."""
    theme = analysis.get("card_theme", "builder")
    
    # Simple theme color mapping
    colors = {
        "hacker": {"bg": "#0d1117", "text": "#c9d1d9", "accent": "#238636"},
        "builder": {"bg": "#f6f8fa", "text": "#24292f", "accent": "#0969da"},
        "researcher": {"bg": "#ffffff", "text": "#1b1f23", "accent": "#6f42c1"},
        "designer": {"bg": "#fff8f2", "text": "#3e2723", "accent": "#d9480f"},
        "open-source-hero": {"bg": "#f0f6ff", "text": "#1d4ed8", "accent": "#10b981"}
    }
    c = colors.get(theme, colors["builder"])

    skills_html = "".join([f'<span class="badge" style="background: {c["accent"]}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8rem; margin-right: 5px;">{skill}</span>' for skill in analysis["top_skills"]])
    
    repos_html = "".join([f'<li><strong>{repo["name"]}</strong> ({repo["stars"]} ⭐) - {repo["language"]}</li>' for repo in github_data["top_repos"][:3]])

    html_template = f"""
    <div class="dev-card" style="background: {c["bg"]}; color: {c["text"]}; border: 1px solid #ddd; border-radius: 15px; padding: 20px; width: 350px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;">
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <img src="{github_data['avatar_url']}" style="width: 60px; height: 60px; border-radius: 50%; margin-right: 15px; border: 2px solid {c['accent']};">
            <div>
                <h2 style="margin: 0; font-size: 1.2rem;">{github_data['name'] or username}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">@{username}</p>
            </div>
        </div>
        <p style="font-style: italic; font-size: 0.95rem; margin-bottom: 15px;">"{analysis['developer_vibe']}"</p>
        <div style="margin-bottom: 15px;">
            {skills_html}
        </div>
        <div style="font-size: 0.85rem; margin-bottom: 15px;">
            <span>📂 {github_data['public_repos']} Repos</span> | <span>👥 {github_data['followers']} Followers</span>
        </div>
        <div style="border-top: 1px solid #eee; padding-top: 10px;">
            <h4 style="margin: 0 0 5px 0; font-size: 0.9rem;">Top Repos</h4>
            <ul style="margin: 0; padding-left: 18px; font-size: 0.8rem;">
                {repos_html}
            </ul>
        </div>
        <p style="font-size: 0.75rem; margin-top: 15px; text-align: right; opacity: 0.6;">✨ {analysis['fun_fact']}</p>
    </div>
    """
    return html_template

@mcp.tool()
async def save_card(username: str, html: str) -> str:
    """Save the HTML to static/cards/{username}.html and return the relative path."""
    output_dir = Path("static/cards")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / f"{username}.html"
    file_path.write_text(html, encoding="utf-8")
    
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
