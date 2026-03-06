# Pilot + Buddy

An AI coding agent with two interfaces: a **CLI terminal** and a **floating desktop assistant** (think Clippy, but useful). Works with any OpenAI-compatible LLM — local (LM Studio, Ollama) or cloud (OpenAI, Anthropic, Groq, etc.).

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

**Pilot** is the brain — an autonomous agent that can:
- Read, write, and edit files
- Run shell commands
- Fetch and scrape web pages
- Control desktop apps (click, type, screenshot, hotkeys)

**Buddy** is the face — a floating animated character that:
- Sits on your desktop with a transparent background
- Chats via speech bubbles and an expandable chat panel
- Animates smoothly at 60 FPS (idle, talking, thinking, waving, error)
- Captures screenshots for vision analysis (full screen or region select)
- Lets you switch LLM providers on the fly via a settings dialog

Both share the same agent core — Buddy just wraps it in a GUI instead of a terminal.

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **An LLM server** — one of:
  - [LM Studio](https://lmstudio.ai/) (local, free) — start a model and enable the local server
  - [Ollama](https://ollama.ai/) (local, free) — `ollama serve`
  - Any cloud API key (OpenAI, Anthropic, Groq, etc.)

### Install

```bash
# Clone the repo
git clone https://github.com/aziz-mezni/miniAgent.git
cd miniAgent

# Install core dependencies
pip install -r requirements.txt

# (Optional) Install Buddy GUI dependencies
pip install -r requirements-buddy.txt
```

### Configure

Edit `config.yaml` to point to your LLM:

```yaml
api:
  base_url: "http://localhost:1234/v1"   # LM Studio default
  api_key: "lm-studio"                   # anything for local
  model: "qwen2.5-coder-32b"            # your loaded model

agent:
  max_iterations: 25
  temperature: 0.7
  system_prompt: |
    You are Pilot, a friendly AI assistant with coding superpowers.
```

**Common base URLs:**

| Provider | Base URL |
|----------|----------|
| LM Studio | `http://localhost:1234/v1` |
| Ollama | `http://localhost:11434/v1` |
| OpenAI | `https://api.openai.com/v1` |
| Groq | `https://api.groq.com/openai/v1` |
| Together AI | `https://api.together.xyz/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |

You can also set config via environment variables:
```bash
export PILOT_API_URL="https://api.openai.com/v1"
export PILOT_API_KEY="sk-..."
export PILOT_MODEL="gpt-4o"
```

---

## Launch

### Terminal Mode (Pilot)

```bash
python -m pilot
```

You'll get an interactive terminal with Rich-formatted output. Type messages, use slash commands:

| Command | Action |
|---------|--------|
| `/help` | Show available commands |
| `/tools` | List all tools the agent can use |
| `/config` | Show current configuration |
| `/clear` | Clear conversation history |
| `/quit` | Exit |

### Desktop Mode (Buddy)

```bash
python -m buddy
```

A floating animated character appears on your desktop. Click it to open the chat panel.

**Header buttons:**
- **🔄** New Session — clears chat history
- **👁** Vision — capture screen for AI analysis (entire screen or draw a region)
- **⚙** Settings — change LLM provider, model, API key, temperature, system prompt

**Right-click** the character for a context menu (toggle chat, clear history, pin/unpin, settings, quit).

The character also lives in your **system tray** — double-click to show/hide.

---

## Project Structure

```
miniAgent/
├── pilot/                    # CLI agent
│   ├── __main__.py           # Entry point
│   ├── agent.py              # Core agent loop (message → LLM → tools → loop)
│   ├── config.py             # Config loader (YAML + env vars)
│   ├── llm.py                # OpenAI-compatible streaming client
│   ├── tool_registry.py      # Tool registration and execution
│   ├── tools/
│   │   ├── base.py           # BaseTool ABC + ToolResult
│   │   ├── file_ops.py       # read_file, write_file, edit_file, glob, grep
│   │   ├── shell.py          # run_command (async subprocess)
│   │   ├── web.py            # fetch_url, scrape_page
│   │   └── app_control.py    # open_app, screenshot, click, type_text, hotkey
│   └── ui/
│       ├── terminal.py       # Interactive terminal with prompt-toolkit
│       └── renderer.py       # Rich-based output rendering
│
├── buddy/                    # Desktop GUI assistant
│   ├── __main__.py           # Entry point
│   ├── app.py                # QApplication + qasync event loop bridge
│   ├── bridge.py             # Duck-types Terminal for agent.py compatibility
│   ├── character.py          # QPainter procedural character (60 FPS)
│   ├── character_config.json # Character appearance config
│   ├── chat_bubble.py        # Floating speech bubble
│   ├── chat_panel.py         # Chat panel with message history
│   ├── main_window.py        # Frameless transparent draggable window
│   ├── screenshot_overlay.py # Region selection overlay for vision
│   ├── settings_panel.py     # Settings dialog (providers, model, prompt)
│   └── tray.py               # System tray icon
│
├── config.yaml               # Main configuration
├── requirements.txt          # Core dependencies
└── requirements-buddy.txt    # GUI dependencies (PySide6, qasync)
```

---

## Tools

The agent has 13 built-in tools exposed to the LLM via function calling:

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents |
| `write_file` | Write/create files |
| `edit_file` | Find-and-replace in files |
| `glob_files` | Search for files by pattern |
| `grep` | Search file contents with regex |
| `run_command` | Execute shell commands (with timeout) |
| `fetch_url` | HTTP GET a URL |
| `scrape_page` | Extract text/links from web pages |
| `open_app` | Launch applications |
| `screenshot` | Capture screen (full or region) |
| `click` | Click at screen coordinates |
| `type_text` | Type text via keyboard |
| `hotkey` | Press keyboard shortcuts |

---

## Dependencies

### Core (`requirements.txt`)
```
openai          — OpenAI-compatible API client
rich            — Terminal formatting
prompt-toolkit  — Interactive input
pyyaml          — Config parsing
httpx           — HTTP client
beautifulsoup4  — HTML parsing
pyautogui       — Desktop automation
pillow          — Image processing
```

### GUI (`requirements-buddy.txt`)
```
PySide6         — Qt6 framework for the desktop UI
qasync          — Bridge between Qt event loop and asyncio
```

---

## Customizing the Character

Edit `buddy/character_config.json` to change the character's appearance:

```json
{
  "name": "Spark",
  "type": "procedural",
  "size": [120, 140],
  "body_color": "#4FC3F7",
  "eye_color": "#FFFFFF",
  "pupil_color": "#1A237E",
  "accent_color": "#FF6F00",
  "cheek_color": "#F48FB1"
}
```

Set `"type": "sprite_sheet"` and provide a `"sprite_sheet"` path to use custom artwork instead of the procedural character.

---

## Architecture

```
User Input
    │
    ▼
┌──────────┐     ┌───────────┐     ┌──────────────┐
│ Terminal  │ or  │   Buddy   │────▶│    Agent      │
│  (CLI)   │     │  (GUI)    │     │  (core loop)  │
└──────────┘     └───────────┘     └──────┬───────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │  LLM Client  │
                                   │  (streaming)  │
                                   └──────┬───────┘
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                         ┌────────┐ ┌──────────┐ ┌────────┐
                         │ Tools  │ │   More   │ │  More  │
                         │(files) │ │ (shell)  │ │ (web)  │
                         └────────┘ └──────────┘ └────────┘
```

The Buddy GUI connects to the same `Agent` via a `BuddyBridge` that duck-types the `Terminal` interface — the agent doesn't know or care which UI is driving it.
