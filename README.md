# RV MCP Server

MCP server bridging Claude to Autodesk/Tweak RV media review application.

## Requirements

- RV 2022.3.1+ with network mode enabled
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

1. **Start RV with networking:**
   ```
   rv.exe -network
   ```
   RV will listen on port 45124 (default).

2. **Register with Claude Code:**
   ```bash
   claude mcp add --scope user rv-mcp -- uv run --directory "H:\001_ProjectCache\1000_Coding\RV_MCP" rv-mcp
   ```

3. **Or add to Claude Desktop** (`~/.claude.json`):
   ```json
   {
     "mcpServers": {
       "rv-mcp": {
         "command": "uv",
         "args": ["run", "--directory", "H:\\001_ProjectCache\\1000_Coding\\RV_MCP", "rv-mcp"]
       }
     }
   }
   ```

## Tools (41 total)

### Execute (1)
- `execute_mu` — Run arbitrary Mu code

### Playback (17)
- `load_source`, `load_sources` — Load media files
- `play`, `stop`, `toggle_playback` — Playback control
- `get_frame`, `set_frame`, `step_forward`, `step_backward` — Frame navigation
- `set_in_point`, `set_out_point`, `get_in_out_points` — In/out points
- `set_fps`, `get_fps`, `set_realtime` — Playback speed
- `set_play_mode`, `set_playback_speed` — Loop mode & direction
- `get_frame_range` — Full frame/playback state as JSON

### Sources (7)
- `get_sources`, `get_source_media_info`, `get_sources_at_frame` — Query sources
- `new_session`, `clear_session`, `save_session` — Session management
- `get_session_info` — Session state as JSON

### Compare (4)
- `set_view_mode` — Switch between sequence/stack/layout views
- `set_composite_type` — Set stack composite mode (over/add/difference/replace)
- `toggle_wipe` — Toggle A/B wipe comparison
- `get_view_info` — Current view state as JSON

### Color (12)
- `set_lut`, `clear_lut` — LUT management
- `set_cdl`, `clear_cdl` — CDL color correction
- `set_exposure`, `set_gamma`, `set_saturation` — Color adjustments
- `get_color_settings` — Current color state as JSON
- `set_display_gamma`, `set_display_srgb` — Display transforms
- `set_background` — Viewport background

## Architecture

```
Claude (stdio/MCP) → FastMCP Server → RV Network Protocol (TCP:45124) → RV
```

No plugin needed inside RV — uses RV's built-in network listener with Mu scripting via `remote-eval`.
