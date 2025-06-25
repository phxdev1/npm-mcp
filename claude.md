# Claude Desktop MCP

> A Model Context Protocol (MCP) server that enables Claude to control desktop operating systems through natural language commands.

## Vision

Transform how users interact with their computers by making Claude an intelligent layer between human intent and system operations. Instead of clicking and typing, users simply describe what they want to accomplish, and Claude handles all the mouse movements, keyboard inputs, and application control.

## What It Does

The Desktop MCP gives Claude the ability to:

- **Control Mouse & Keyboard**: Click, type, drag, scroll, keyboard shortcuts
- **Manage Applications**: Launch, close, switch between apps, window management  
- **File System Operations**: Browse directories, open files, create folders, move/copy files
- **System Monitoring**: Check processes, system resources, take screenshots
- **Web Automation**: Control browsers, fill forms, navigate websites
- **Workflow Automation**: Chain complex multi-step operations across applications

## User Experience

```
User: "Open my email and archive all messages from last week"
Claude: Opening Mail app... Found 23 messages from June 18-24... Archiving... Done!

User: "Create a presentation about Q1 sales using data from my spreadsheet"  
Claude: Opening Excel to get your Q1 data... Found sales figures... Creating PowerPoint... 
       Imported charts and tables... Presentation saved as "Q1_Sales_Report.pptx"

User: "Show me my photos from vacation and create a slideshow"
Claude: Scanning Photos app... Found 47 vacation photos from Italy trip... 
       Creating slideshow with transitions... Would you like me to add music?
```

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
                                                        │
                                               ┌─────────────────┐
                                               │  Operating      │
                                               │  System         │
                                               │                 │
                                               │ • Windows       │
                                               │ • macOS         │
                                               │ • Linux         │
                                               └─────────────────┘
```

## Core Functions

### Mouse & Keyboard Control
```python
@mcp_function
def click_at(x: int, y: int, button: str = "left") -> bool:
    """Click at specific screen coordinates"""

@mcp_function  
def type_text(text: str, interval: float = 0.0) -> bool:
    """Type text with optional delay between characters"""

@mcp_function
def key_combination(keys: List[str]) -> bool:
    """Execute keyboard shortcuts (e.g., ['ctrl', 'c'])"""

@mcp_function
def drag_and_drop(start_x: int, start_y: int, end_x: int, end_y: int) -> bool:
    """Drag from start coordinates to end coordinates"""
```

### Application Management
```python
@mcp_function
def launch_application(app_name: str) -> bool:
    """Launch application by name or executable path"""

@mcp_function
def get_open_windows() -> List[WindowInfo]:
    """Get list of all open windows with titles and positions"""

@mcp_function
def focus_window(title: str) -> bool:
    """Bring window to foreground by title"""

@mcp_function
def close_window(title: str) -> bool:
    """Close window by title"""
```

### File System Operations
```python
@mcp_function
def list_directory(path: str) -> List[FileInfo]:
    """List files and folders in directory"""

@mcp_function
def open_file(file_path: str) -> bool:
    """Open file with default application"""

@mcp_function
def create_directory(path: str) -> bool:
    """Create new directory"""

@mcp_function
def move_file(source: str, destination: str) -> bool:
    """Move or rename file/directory"""
```

### System Information
```python
@mcp_function
def take_screenshot(region: Optional[Tuple[int, int, int, int]] = None) -> str:
    """Take screenshot and return as base64 encoded image"""

@mcp_function
def get_system_stats() -> SystemStats:
    """Get CPU, memory, disk usage information"""

@mcp_function
def get_running_processes() -> List[ProcessInfo]:
    """Get list of running processes"""
```

## Implementation

### Technology Stack
- **Python 3.8+**: Core server implementation
- **MCP SDK**: Model Context Protocol framework
- **PyAutoGUI**: Cross-platform GUI automation
- **psutil**: System and process utilities
- **Pillow**: Image processing for screenshots
- **pygetwindow**: Window management utilities

### Platform Support
- ✅ **Windows**: Full support via Win32 APIs
- ✅ **macOS**: Support via Accessibility APIs  
- ✅ **Linux**: Support via X11/Wayland

### Safety Features
- **Permissions System**: Fine-grained control over what actions are allowed
- **Confirmation Prompts**: Optional user confirmation for destructive operations
- **Action Logging**: Complete audit trail of all operations
- **Sandboxing**: Restrict operations to specific directories/applications
- **Emergency Stop**: Immediate halt mechanism for runaway automation

## Installation

### Prerequisites
```bash
# Install Python dependencies
pip install mcp-sdk pyautogui psutil pillow pygetwindow

# Platform-specific requirements
# Windows: No additional requirements
# macOS: Enable Accessibility permissions
# Linux: Install xdotool, scrot
```

### Quick Start
```bash
# Install Desktop MCP
pip install desktop-mcp

# Install any NPM plugins you want (zero config!)
npm install -g desktop-mcp-mouse
npm install -g desktop-mcp-keyboard  
npm install -g desktop-mcp-browser

# Run the server (auto-discovers all plugins)
desktop-mcp

# That's it! All installed plugins are automatically available
```

### Zero-Configuration Plugin System
```bash
# Want mouse control? Just install robotjs:
npm install -g robotjs

# Want browser automation? Just install puppeteer:
npm install -g puppeteer

# Want enhanced file operations? Just install fs-extra:
npm install -g fs-extra

# Want system monitoring? Just install systeminformation:
npm install -g systeminformation

# Everything works immediately - existing packages are auto-adapted!
```

## Security Considerations

### Permissions Model
```yaml
permissions:
  mouse_keyboard: 
    enabled: true
    confirmation_required: false
    
  file_system:
    enabled: true
    allowed_paths: ["~/Documents", "~/Downloads"]
    confirmation_required: true
    
  applications:
    enabled: true
    blocked_apps: ["Terminal", "Command Prompt"]
    confirmation_required: false
    
  system_control:
    enabled: false  # Disabled by default
    confirmation_required: true
```

### Best Practices
- Run with minimal required privileges
- Enable confirmation prompts for destructive operations
- Regularly review action logs
- Use application allowlists in production
- Monitor for unusual automation patterns

## Development Roadmap

### Phase 1: Core Functionality ✨ 
- [x] Basic mouse/keyboard control
- [x] Window management
- [x] File system operations
- [x] Screenshot capability
- [ ] Cross-platform testing

### Phase 2: Advanced Features 🚀
- [ ] Web browser automation
- [ ] Application-specific integrations
- [ ] Workflow recording and playback
- [ ] Computer vision for UI element detection
- [ ] Voice command integration

### Phase 3: Intelligence Layer 🧠
- [ ] Context awareness across sessions
- [ ] Predictive automation
- [ ] Learning from user patterns
- [ ] Integration with other MCP servers
- [ ] Multi-modal input (voice + vision)

## Contributing

We welcome contributions! Please see:
- [Contributing Guidelines](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Development Setup](docs/development.md)

### Areas Needing Help
- Platform-specific implementations
- Security and permissions frameworks
- Application-specific automation modules
- Documentation and examples
- Testing across different environments

## Examples

### File Management
```python
# User: "Organize my Downloads folder by file type"
await list_directory("~/Downloads")
await create_directory("~/Downloads/Images")  
await create_directory("~/Downloads/Documents")
await move_file("~/Downloads/photo.jpg", "~/Downloads/Images/")
```

### Application Workflow
```python
# User: "Send the quarterly report to my team"
await launch_application("Mail")
await click_at(compose_button_coords)
await type_text("team@company.com")
await key_combination(["tab"])
await type_text("Q1 Report")
await click_at(attach_button_coords)
# ... continue workflow
```

### System Administration
```python
# User: "Check what's using the most CPU"
processes = await get_running_processes()
stats = await get_system_stats()
screenshot = await take_screenshot()
# Analyze and report findings
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

- Built on the [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk)
- Inspired by the vision of conversational computing
- Thanks to the Claude AI team at Anthropic

---

**⚠️ Important**: This tool provides powerful system access. Please use responsibly and review all security considerations before deployment.