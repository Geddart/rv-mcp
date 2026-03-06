# RV MCP Server

MCP (Model Context Protocol) server that bridges AI assistants like Claude to **Autodesk/Tweak RV**, the industry-standard media review application. Control playback, compare shots, adjust color grading, and manage review sessions — all through natural language.

No plugin required inside RV. Uses RV's built-in network listener with Mu scripting via `remote-eval`.

## Requirements

- **RV 2022.3.1+** with network mode enabled (`-network` flag)
- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** package manager

## Quick Start

### 1. Start RV with networking

```bash
rv -network
```

RV will listen on port **45124** (default). On Windows:

```cmd
"C:\Program Files\ShotGrid\RV-2022.3.1\bin\rv.exe" -network -networkPort 45124
```

### 2. Install and register

**Claude Code (CLI):**

```bash
claude mcp add --scope user rv-mcp -- uv run --directory /path/to/RV_MCP rv-mcp
```

**Claude Desktop** (`~/.claude.json`):

```json
{
  "mcpServers": {
    "rv-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/RV_MCP", "rv-mcp"]
    }
  }
}
```

### 3. Use it

Ask Claude to load media, control playback, compare shots, or adjust colors. The server translates natural language into RV commands automatically.

## Architecture

```
Claude (stdio/MCP) --> FastMCP Server --> RV Network Protocol (TCP:45124) --> RV
```

The server maintains a **persistent TCP connection** to RV using a custom protocol based on RV's `RvCommunicator`. Key design decisions:

- **Persistent connection** with automatic reconnection on socket loss
- **Thread-safe** via `threading.Lock` for concurrent tool calls
- **Clean shutdown** via `atexit` handler that sends `DISCONNECT` (without this, RV rejects future connections)
- **Mu string handling** — return values are automatically unquoted and unescaped

### Protocol Flow

```
1. Connect TCP to 127.0.0.1:45124
2. Send: NEWGREETING <len> rv-mcp rvController
3. Send: PINGPONGCONTROL 1 0          (disable heartbeat)
4. Recv: NEWGREETING <len> <rv-name>   (consume RV's greeting)
5. For each command:
   Send: MESSAGE <len> RETURNEVENT remote-eval * { require commands; <mu_code> }
   Recv: MESSAGE <len> RETURN <value>
6. On shutdown:
   Send: MESSAGE <len> DISCONNECT
```

## Tools (41 total)

### Execute (1)

| Tool | Description |
|------|-------------|
| `execute_mu` | Run arbitrary Mu code — escape hatch for anything not covered by dedicated tools |

### Playback (17)

| Tool | Description |
|------|-------------|
| `load_source` | Load a media file (image sequence, movie, or single image) |
| `load_sources` | Load multiple media files at once |
| `play` | Start playback |
| `stop` | Stop playback |
| `toggle_playback` | Toggle play/stop, returns new state |
| `get_frame` | Get current frame number |
| `set_frame` | Jump to a specific frame |
| `step_forward` | Step forward by N frames (default 1) |
| `step_backward` | Step backward by N frames (default 1) |
| `set_in_point` | Set the in-point (start of playback range) |
| `set_out_point` | Set the out-point (end of playback range) |
| `get_in_out_points` | Get current in/out points as JSON |
| `set_fps` | Set playback frames per second |
| `get_fps` | Get current playback FPS |
| `set_realtime` | Enable/disable realtime mode (skip frames to maintain FPS) |
| `set_play_mode` | Set loop mode: `loop`, `once`, or `pingpong` |
| `set_playback_speed` | Set playback direction and speed (1=forward, -1=reverse, 2=2x, etc.) |
| `get_frame_range` | Get full playback state as JSON (frame, range, in/out, playing, fps) |

### Sources (7)

| Tool | Description |
|------|-------------|
| `get_sources` | List all loaded source nodes as JSON array |
| `get_source_media_info` | Get detailed media info (resolution, frame range, fps, bit depth, channels) |
| `get_sources_at_frame` | Get source nodes visible at a specific frame |
| `new_session` | Create a new empty session |
| `clear_session` | Clear all sources from the current session |
| `save_session` | Save session to an `.rv` file |
| `get_session_info` | Get session state as JSON (view node, frame range, source count) |

### Compare (4)

| Tool | Description |
|------|-------------|
| `set_view_mode` | Switch view: `sequence` (play in order), `stack` (layer for comparison), `layout` (tile side by side) |
| `set_composite_type` | Set stack composite mode: `over`, `add`, `difference`, `-difference`, `replace`, `topmost` |
| `toggle_wipe` | Toggle A/B wipe comparison (auto-switches to stack view) |
| `get_view_info` | Get current view state as JSON |

### Color (12)

| Tool | Description |
|------|-------------|
| `set_lut` | Load a LUT file (`.3dl`, `.csp`, `.cube`, etc.) on a target (`look`, `linearize`, `display`) |
| `clear_lut` | Deactivate LUT on a target |
| `set_cdl` | Set CDL values (slope, offset, power, saturation) — partial updates supported |
| `clear_cdl` | Deactivate CDL color correction |
| `set_exposure` | Set exposure (per-channel or uniform) |
| `set_gamma` | Set gamma correction |
| `set_saturation` | Set saturation |
| `get_color_settings` | Get current color correction state as JSON |
| `set_display_gamma` | Set display gamma (e.g., 2.2 for sRGB-like) |
| `set_display_srgb` | Enable/disable sRGB display transform |
| `set_background` | Set viewport background: `black`, `checker`, `grey18`, `grey50`, `crosshatch` |

## Usage Examples

### Load and review footage

```
"Load the EXR sequence at /shots/sh010/comp/sh010_comp.1-100#.exr"
"Play it back at 24fps"
"Go to frame 50"
"Set in point at 20 and out point at 80"
```

### Compare two versions

```
"Load both /shots/sh010/comp_v1.mov and /shots/sh010/comp_v2.mov"
"Switch to stack view"
"Set composite to difference mode"
"Toggle the wipe to compare side by side"
```

### Color correction

```
"Apply CDL with slope [1.1, 0.95, 1.0] and saturation 1.2"
"Load the ACES LUT from /luts/sRGB.cube"
"Set exposure to 0.5"
"Show me the current color settings"
```

### Advanced (raw Mu)

```
"Execute this Mu code: { require commands; let s = sources(); string(s.size()); }"
```

## Project Structure

```
RV_MCP/
├── pyproject.toml          # Package config, entry point, dependencies
├── README.md
├── .gitignore
└── src/
    ├── __init__.py
    ├── server.py           # FastMCP server + RvClient instantiation
    ├── rv_client.py        # Persistent TCP client (RV network protocol)
    └── tools/
        ├── __init__.py
        ├── execute.py      # execute_mu — raw Mu escape hatch
        ├── playback.py     # 17 playback/transport tools
        ├── sources.py      # 7 source & session tools
        ├── compare.py      # 4 view/compare tools
        └── color.py        # 12 color/LUT/CDL tools
```

## Troubleshooting

### "Could not connect to RV"

- Ensure RV is running with the `-network` flag
- Check that port 45124 is not blocked by a firewall
- Use `-networkPort 45124` to explicitly set the port

### RV rejects connections after a crash

If the server exits without sending `DISCONNECT`, RV may reject new connections. Restart RV to clear the state. The server includes an `atexit` handler to prevent this under normal operation.

### Mu code errors

- Always wrap code blocks in `{ require commands; ... }`
- Mu evaluates both branches of `if/then/else` — avoid property access on nodes that may not exist
- File paths must use forward slashes; `escape_mu_string()` handles this automatically

### Timeout errors

The default timeout is 30 seconds. If Mu code takes longer (e.g., loading large sequences), it may time out. Use `execute_mu` for long operations and consider breaking them into smaller steps.

## Development

```bash
# Install dependencies
uv sync

# Run the server directly
uv run rv-mcp

# Run with debug logging
uv run python -m src.server
```

## License

MIT
