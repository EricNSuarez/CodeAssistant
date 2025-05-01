import os
import sys
import glob
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

import openai
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.theme import Theme
from rich.progress import Progress
from rich.syntax import Syntax

# Define custom theme
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
})

console = Console(theme=custom_theme)

# Available AI models - Using OpenRouter models
MODELS = {
    "openrouter/anthropic/claude-3-5-sonnet": {"provider": "openrouter", "name": "Claude 3.5 Sonnet"},
    "openrouter/anthropic/claude-3-opus": {"provider": "openrouter", "name": "Claude 3 Opus"},
    "openrouter/anthropic/claude-3-haiku": {"provider": "openrouter", "name": "Claude 3 Haiku"},
    "openrouter/google/gemini-pro": {"provider": "openrouter", "name": "Gemini Pro"},
    "openrouter/openai/gpt-4o": {"provider": "openrouter", "name": "GPT-4o"},
    "openrouter/mistral/mistral-large": {"provider": "openrouter", "name": "Mistral Large"},
    "openrouter/meta-llama/llama-3-70b-instruct": {"provider": "openrouter", "name": "Llama 3 70B"},
    "google/gemini-2.5-flash-preview": {"provider": "openrouter", "name": "Gemini 2.5 Flash Preview"},
}

def load_env_file() -> Dict[str, str]:
    """Load environment variables from .env file if it exists."""
    env_vars = {}
    
    if os.path.exists(".env"):
        console.print("[info]Found .env file, loading environment variables...[/info]")
        try:
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    # Look for key=value pattern
                    match = re.match(r"^([A-Za-z0-9_]+)=(.*)$", line)
                    if match:
                        key = match.group(1)
                        value = match.group(2).strip('"\'')
                        env_vars[key] = value
                        
            console.print(f"[success]Loaded {len(env_vars)} environment variables from .env file[/success]")
        except Exception as e:
            console.print(f"[warning]Error loading .env file: {str(e)}[/warning]")
    
    return env_vars

def check_git_repository() -> bool:
    """Verify if the current directory is a git repository."""
    return os.path.isdir(".git")

def get_gitignore_patterns() -> List[str]:
    """Get patterns from .gitignore file."""
    if not os.path.exists(".gitignore"):
        return []
    
    with open(".gitignore", "r") as f:
        lines = f.readlines()
    
    patterns = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    
    return patterns

def should_ignore(file_path: str, ignore_patterns: List[str]) -> bool:
    """Check if a file should be ignored based on gitignore patterns."""
    for pattern in ignore_patterns:
        if pattern.endswith('/'):  # Directory pattern
            if file_path.startswith(pattern) or f"/{pattern}" in file_path:
                return True
        elif pattern.startswith('*.'):  # Extension pattern
            extension = pattern[1:]
            if file_path.endswith(extension):
                return True
        elif pattern in file_path or f"/{pattern}" in file_path:
            return True
    return False

def read_file_content(file_path: str) -> str:
    """Read content of a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def get_repository_files(ignore_patterns: List[str]) -> Dict[str, str]:
    """Get all files in the repository excluding those matching gitignore patterns."""
    files = {}
    
    for file_path in glob.glob("**/*", recursive=True):
        if os.path.isfile(file_path) and not should_ignore(file_path, ignore_patterns) and not ".git/" in file_path:
            files[file_path] = read_file_content(file_path)
    
    return files

def get_git_info() -> Dict[str, Any]:
    """Get git repository information."""
    info = {}
    try:
        # Get current branch
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
        info["branch"] = branch
        
        # Get remote URL
        remote = subprocess.check_output(["git", "config", "--get", "remote.origin.url"]).decode().strip()
        info["remote"] = remote
        
        # Get last commit
        last_commit = subprocess.check_output(["git", "log", "-1", "--pretty=%B"]).decode().strip()
        info["last_commit"] = last_commit
        
    except subprocess.CalledProcessError:
        pass
    
    return info

def generate_system_prompt(files: Dict[str, str], git_info: Dict[str, Any],
                           single_file: Optional[str] = None) -> str:
    """Generate system prompt with repository information."""
    system_prompt = f"""You are a helpful code assistant answering questions about the user's code repository.

Repository Information:
- Branch: {git_info.get('branch', 'Unknown')}
- Remote: {git_info.get('remote', 'Unknown')}
- Last Commit Message: {git_info.get('last_commit', 'Unknown')}

Files in the repository:
"""
    if single_file:
        system_prompt += f"\n(Focusing analysis on: {single_file})\n"
    
    for file_path in files.keys():
        system_prompt += f"- {file_path}\n"
    
    system_prompt += "\nPlease provide helpful, accurate answers about the code in this repository."
    return system_prompt

def get_file_content_for_context(files: Dict[str, str], max_tokens: int = 16000) -> str:
    """Get file content for context, limiting to max_tokens. Newline between files for clarity."""
    context = ""
    current_tokens = 0
    
    for file_path, content in files.items():
        estimated_tokens = len(content) // 4  # Rough estimate
        
        if current_tokens + estimated_tokens > max_tokens:
            break
        
        context += f"\n\n# File: {file_path}\n```\n{content}\n```"
        current_tokens += estimated_tokens
    
    return context

def query_openrouter(system_prompt: str, user_prompt: str, model: str) -> str:
    """Query OpenRouter's API."""
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=4000
    )
    return response.choices[0].message.content

def query_openai(system_prompt: str, user_prompt: str, model: str) -> str:
    """Query OpenAI's API."""
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=4000
    )
    return response.choices[0].message.content

def query_ai(system_prompt: str, user_prompt: str, model: str) -> str:
    """Query the AI model based on the provider."""
    with Progress() as progress:
        task = progress.add_task("[cyan]Querying AI model...", total=1)
        
        try:
            if MODELS[model]["provider"] == "openrouter":
                response = query_openrouter(system_prompt, user_prompt, model)
            elif MODELS[model]["provider"] == "openai":
                response = query_openai(system_prompt, user_prompt, model)
            else:
                response = "Error: Unknown model provider"
                
            progress.update(task, completed=1)
            return response
        except Exception as e:
            progress.update(task, completed=1)
            return f"Error querying AI: {str(e)}"

def display_file_preview(file_path: str, content: str) -> None:
    """Display a preview of a file with syntax highlighting."""
    console.print(f"\n[bold blue]File: {file_path}[/bold blue]")
    
    # Determine language based on file extension
    extension = file_path.split('.')[-1] if '.' in file_path else ''
    language_map = {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'html': 'html',
        'css': 'css',
        'json': 'json',
        'md': 'markdown',
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp',
        'rs': 'rust',
        'go': 'go',
    }
    
    language = language_map.get(extension, 'text')
    syntax = Syntax(content[:500] + ("..." if len(content) > 500 else ""), language, theme="monokai")
    console.print(syntax)

def save_response_to_file(filename: str, content: str) -> None:
    """
    Saves content to a specified file, prompting for overwrite if it exists.
    If the content is detected as a Markdown code block, the delimiters and language are trimmed.
    """
    file_path = Path(filename)

    if file_path.exists():
        if file_path.is_file():
            overwrite = Prompt.ask(f"[warning]File '{filename}' already exists. Overwrite?[/warning]",
                                   choices=['y', 'n'], default='n')
            if overwrite.lower() == 'n':
                console.print("[info]File save cancelled.[/info]")
                return
        else:
            console.print(f"[error]Error: Cannot save. '{filename}' exists and is not a file (e.g., it's a directory).[/error]")
            return

    # Check if the content is a Markdown code block and trim if necessary
    trimmed_content = content
    # Regex to find a Markdown code block definition at the start of the string
    code_block_match = re.search(r"^\s*```(\w+)?\n(.*?)\n```\s*$", content, re.DOTALL)

    if code_block_match:
        trimmed_content = code_block_match.group(2)
        console.print("[info]Detected and trimmed markdown code block delimiters.[/info]")
    else:
        # Also check for inline code blocks and remove backticks if the *entire* content is an inline block
        inline_code_match = re.match(r"^\s*`(.*)`\s*$", content, re.DOTALL)
        if inline_code_match:
            trimmed_content = inline_code_match.group(1)
            console.print("[info]Detected and trimmed markdown inline code delimiters.[/info]")

    try:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(trimmed_content)
        console.print(f"[success]Response successfully saved to '{filename}'[/success]")
    except IOError as e:
        console.print(f"[error]Error writing file '{filename}': {e}[/error]")
    except Exception as e:
        console.print(f"[error]An unexpected error occurred while saving file '{filename}': {e}[/error]")

def check_api_keys() -> bool:
    """Check if required API keys are set in environment or .env file."""
    # First, load environment variables from .env file
    env_vars = load_env_file()
    
    # Add .env vars to environment
    for key, value in env_vars.items():
        os.environ[key] = value
    
    required_keys = ["OPENROUTER_API_KEY"]
    missing_keys = [key for key in required_keys if key not in os.environ]
    
    if missing_keys:
        console.print(Panel.fit(
            "Required API keys are not set. Please set the following environment variables:\n" +
            "\n".join([f"- {key}" for key in missing_keys]),
            title="API Keys Missing",
            border_style="red"
        ))
        console.print("\nYou can set them by:")
        console.print("1. Creating a .env file in the current directory with:")
        for key in missing_keys:
            console.print(f"   {key}=your_api_key_here")
        console.print("\n2. OR setting environment variables:")
        for key in missing_keys:
            console.print(f"   export {key}=your_api_key_here")
        return False
    return True

def main() -> None:
    """Main function for the code assistant."""
    parser = argparse.ArgumentParser(description="AI-powered code assistant for Git repositories")
    parser.add_argument("file", nargs="?", help="Optional: Specify a single file to analyze")
    parser.add_argument("--model", choices=list(MODELS.keys()), default="google/gemini-2.5-flash-preview", help="AI model to use")
    args = parser.parse_args()
    
    # Print welcome message
    console.print(Panel.fit(
        "[bold blue]Code Assistant[/bold blue] - AI-powered code assistant for your repository",
        title="Welcome",
        border_style="blue"
    ))
    
    # Check for API keys (including from .env file)
    if not check_api_keys():
        sys.exit(1)
    
    # Check for Git repository
    if not check_git_repository():
        console.print("[error]Error: Not a valid Git repository. Please run this from a Git repository root.[/error]")
        sys.exit(1)
    
    # Get gitignore patterns
    ignore_patterns = get_gitignore_patterns()
    console.print(f"Found [info]{len(ignore_patterns)}[/info] gitignore patterns.")
    
    # Get repository files
    with Progress() as progress:
        task = progress.add_task("[cyan]Scanning repository files...", total=1)
        files = get_repository_files(ignore_patterns)
        progress.update(task, completed=1)
    
    console.print(f"Found [success]{len(files)}[/success] files in the repository.")
    
    # Get git information
    git_info = get_git_info()

    # If a single file is specified, read and provide its content
    if args.file:
        if args.file in files:
            single_file_content = read_file_content(args.file)
            console.print(f"[info]Analyzing only: [/info][bold]{args.file}[/bold]")
            # Update the system prompt and context to reflect the single file analysis
            files_to_analyze = {args.file: single_file_content}
            system_prompt = generate_system_prompt(files_to_analyze, git_info, single_file=args.file)
            # context = f"\n# File: {args.file}\n```\n{single_file_content}\n```"
        else:
             console.print(
                 f"[error]Error: Specified file '{args.file}' not found in the repository or is ignored.[/error]")
             sys.exit(1)
    else:
        # Generate system prompt
        system_prompt = generate_system_prompt(files, git_info)
    
    # Add file contents to context
    context = get_file_content_for_context(files)
    
    # Add context to system prompt
    system_prompt += "\n\nHere are the contents of important files in the repository:" + context

    # Variable to store the last AI response
    last_response: Optional[str] = None

    while True:
        console.print(f"\nUsing model: [bold]{MODELS[args.model]['name']}[/bold]")
        
        # Get user query
        user_query = Prompt.ask("\n[bold green]Ask about your code[/bold green] (type 'exit' to quit, 'model' to change model, 'preview <file>' to see a file, 'save response <filename>' to save last response)")
        
        if user_query.lower() == 'exit':
            break
        elif user_query.lower() == 'model':
            # Display available models
            console.print("\n[bold]Available models:[/bold]")
            for key, model_info in MODELS.items():
                console.print(f"  - {key}: {model_info['name']} ({model_info['provider']})")
            
            # Let user select a model
            new_model = Prompt.ask("[bold]Select model[/bold]", choices=list(MODELS.keys()))
            args.model = new_model
            console.print(f"[success]Changed to {MODELS[new_model]['name']}[/success]")
            continue
        elif user_query.lower().startswith('preview '):
            file_path = user_query[8:].strip()
            if file_path in files:
                display_file_preview(file_path, files[file_path])
            else:
                console.print(f"[error]File not found: {file_path}[/error]")
            continue
        elif user_query.lower().startswith('save response '):
            parts = user_query.split(' ', 2)  # Split into 'save', 'response', '<filename>'
            if len(parts) < 3 or not parts[2].strip():
                console.print("[warning]Please provide a filename, e.g., 'save response new_file.py'[/warning]")
            elif last_response is None:
                console.print("[warning]No AI response available to save yet. Ask a question first.[/warning]")
            else:
                filename_to_save = parts[2].strip()
                save_response_to_file(filename_to_save, last_response)  # Call the new save function
            continue  # Continue the loop after attempting to save
        
        # Query AI
        response = query_ai(system_prompt, user_query, args.model)

        # Store the last response
        last_response = response

        # Display response
        console.print("\n[bold]Response:[/bold]")
        console.print(Markdown(response))

if __name__ == "__main__":
    main()