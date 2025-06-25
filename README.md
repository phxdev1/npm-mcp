# Desktop MCP Server

A Model Context Protocol (MCP) server that enables Claude to control desktop operating systems through natural language commands.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   npm install
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Run the server:**
   ```bash
   python -m desktop_mcp.server
   ```

## Features

- **Mouse & Keyboard Control**: Click, type, drag, scroll, keyboard shortcuts
- **Application Management**: Launch, close, switch between apps, window management  
- **File System Operations**: Browse directories, open files, create folders, move/copy files
- **System Monitoring**: Check processes, system resources, take screenshots
- **Text-to-Speech**: Convert text to speech using ElevenLabs
- **Web Automation**: Control browsers, fill forms, navigate websites
- **Database Operations**: SQLite database management
- **Task Scheduling**: Schedule and manage automated tasks

## Configuration

The server auto-discovers and loads all available adapters from the `desktop_mcp/adapters/` directory. Each adapter is a JSON file that defines how to interface with different tools and libraries.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude AI     │◄──►│   MCP Client    │◄──►│  Desktop MCP    │
│                 │    │                 │    │     Server      │
│ • Natural       │    │ • Protocol      │    │ • OS APIs       │
│   Language      │    │   Handler       │    │ • Automation    │
│ • Reasoning     │    │ • Connection    │    │ • Safety        │
│ • Planning      │    │   Management    │    │ • Execution     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Available Tools

- **Speech**: `speak_text`, `save_speech_to_file`, `get_voices`
- **System**: `run_command`, `get_environment_variable`, `get_current_directory`
- **Clipboard**: `get_clipboard_text`, `set_clipboard_text`, `clear_clipboard`
- **HTTP**: `http_get`, `http_post`, `download_file`, `check_website_status`
- **Database**: `create_database`, `execute_query`, `create_table`, `insert_data`
- **Scheduling**: `schedule_task`, `schedule_daily_task`, `list_scheduled_tasks`

## License

MIT License - See LICENSE for details.