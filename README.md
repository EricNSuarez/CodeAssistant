# Code Assistant 🤖💻

An AI-powered command-line tool that helps me understand and interact with my code repositories through natural language queries.
 
*[Placeholder for a demo GIF]*

## ✨ Key Features

- **Smart Repository Analysis** - Scans your Git repository while respecting `.gitignore` rules.
- **Git Context Awareness** - Retrieves branch info, remote origin, and commit history.
- **AI-Powered Insights** - Answers questions about code using LLMs via OpenRouter API.
- **Multi-Model Support** - Choose from various language models.
- **Developer-Friendly** - File previews, syntax highlighting, and clean output formatting.

## 🛠️ Tech Stack

- Python 3.6+
- OpenRouter API
- Git integration
- Rich library for beautiful terminal formatting

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/EricNSuarez/CodeAssistant.git
   cd CodeAssistant
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🔑 Configuration

1. Get your [OpenRouter API key](https://openrouter.ai/)
2. Set up your environment:

   **Option 1:** Create a `.env` file
   ```env
   OPENROUTER_API_KEY=your_api_key_here
   ```

   **Option 2:** Set in your shell config (`.bashrc`, `.zshrc`)
   ```bash
   export OPENROUTER_API_KEY=your_api_key_here
   ```

## 🚀 Usage

### Basic Usage
```bash
python code_assistant.py
```

### Analyze Specific File
```bash
python code_assistant.py path/to/file.py
```

### Specify AI Model
```bash
python code_assistant.py --model openrouter/anthropic/claude-3-opus
```

### Interactive Commands
- Ask questions about your code
- `model`: List available models or switch models
- `preview <file_path>`: View file contents
- `exit`: Quit the assistant

## 🧠 How It Works

The assistant follows this workflow:

1. **Initialization**:
   - Loads configuration and API keys
   - Verifies Git repository status
   - Parses `.gitignore` rules

2. **Repository Analysis**:
   - Scans directory structure
   - Reads relevant file contents (respecting token limits)
   - Gathers Git context (branch, remotes, commits)

3. **AI Interaction**:
   - Constructs comprehensive system prompt
   - Processes user queries with full context
   - Formats responses with syntax highlighting

## 🌱 Future Enhancements

- [ ] Implement conversation history

## 📄 License

MIT License