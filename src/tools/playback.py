from ..server import mcp, client
from ..rv_client import escape_mu_string


@mcp.tool()
def load_source(file_path: str) -> str:
    """Load a media file (image sequence, movie, or single image) into RV.

    Args:
        file_path: Path to the media file. For sequences use RV notation
                   e.g. "/path/to/image.1-100#.exr" or just the path to one frame.
    """
    safe = escape_mu_string(file_path)
    code = (
        '{ require commands;'
        f' addSourceVerbose("{safe}");'
        ' }'
    )
    return client.eval_mu(code)


@mcp.tool()
def load_sources(file_paths: list[str]) -> str:
    """Load multiple media files into RV at once.

    Args:
        file_paths: List of paths to media files.
    """
    items = ", ".join(f'"{escape_mu_string(p)}"' for p in file_paths)
    code = (
        '{ require commands;'
        f' addSources(string[] {{{items}}});'
        ' "sources loaded";'
        ' }'
    )
    return client.eval_mu(code)


@mcp.tool()
def play() -> str:
    """Start playback in RV."""
    return client.eval_mu('{ require commands; play(); "playing"; }')


@mcp.tool()
def stop() -> str:
    """Stop playback in RV."""
    return client.eval_mu('{ require commands; stop(); "stopped"; }')


@mcp.tool()
def toggle_playback() -> str:
    """Toggle play/stop in RV. Returns the new state."""
    return client.eval_mu(
        '{ require commands;'
        ' if isPlaying() then { stop(); "stopped"; }'
        ' else { play(); "playing"; };'
        ' }'
    )


@mcp.tool()
def get_frame() -> str:
    """Get the current frame number in RV."""
    return client.eval_mu('{ require commands; string(frame()); }')


@mcp.tool()
def set_frame(frame: int) -> str:
    """Go to a specific frame in RV.

    Args:
        frame: The frame number to jump to.
    """
    return client.eval_mu(
        f'{{ require commands; setFrame({frame}); string(frame()); }}'
    )


@mcp.tool()
def step_forward(count: int = 1) -> str:
    """Step forward by N frames.

    Args:
        count: Number of frames to step forward (default 1).
    """
    return client.eval_mu(
        f'{{ require commands; setFrame(frame() + {count}); string(frame()); }}'
    )


@mcp.tool()
def step_backward(count: int = 1) -> str:
    """Step backward by N frames.

    Args:
        count: Number of frames to step backward (default 1).
    """
    return client.eval_mu(
        f'{{ require commands; setFrame(frame() - {count}); string(frame()); }}'
    )


@mcp.tool()
def set_in_point(frame: int) -> str:
    """Set the in-point (start of playback range).

    Args:
        frame: Frame number for the in-point.
    """
    return client.eval_mu(
        f'{{ require commands; setInPoint({frame}); string(inPoint()); }}'
    )


@mcp.tool()
def set_out_point(frame: int) -> str:
    """Set the out-point (end of playback range).

    Args:
        frame: Frame number for the out-point.
    """
    return client.eval_mu(
        f'{{ require commands; setOutPoint({frame}); string(outPoint()); }}'
    )


@mcp.tool()
def get_in_out_points() -> str:
    """Get the current in/out points as JSON."""
    return client.eval_mu(
        r'{ require commands;'
        r' "{\"inPoint\":" + string(inPoint())'
        r' + ",\"outPoint\":" + string(outPoint()) + "}";'
        r' }'
    )


@mcp.tool()
def set_fps(fps: float) -> str:
    """Set the playback frames per second.

    Args:
        fps: Target FPS value.
    """
    return client.eval_mu(
        f'{{ require commands; setFPS({fps}); string(fps()); }}'
    )


@mcp.tool()
def get_fps() -> str:
    """Get the current playback FPS."""
    return client.eval_mu('{ require commands; string(fps()); }')


@mcp.tool()
def set_realtime(enabled: bool = True) -> str:
    """Enable or disable realtime playback mode.

    When enabled, RV will skip frames to maintain the target FPS.

    Args:
        enabled: True to enable realtime, False to play every frame.
    """
    val = "true" if enabled else "false"
    return client.eval_mu(
        f'{{ require commands; setRealtime({val});'
        f' if isRealtime() then "realtime on" else "realtime off"; }}'
    )


@mcp.tool()
def set_play_mode(mode: str = "loop") -> str:
    """Set the playback loop mode.

    Args:
        mode: One of "loop", "once", or "pingpong".
    """
    mode_map = {
        "loop": "PlayLoop",
        "once": "PlayOnce",
        "pingpong": "PlayPingPong",
    }
    mu_mode = mode_map.get(mode.lower())
    if not mu_mode:
        return f"Invalid mode '{mode}'. Use: loop, once, pingpong"
    return client.eval_mu(
        f'{{ require commands; setPlayMode({mu_mode}); "{mode}"; }}'
    )


@mcp.tool()
def get_frame_range() -> str:
    """Get the full frame range and current state as JSON.

    Returns JSON with: frame, frameStart, frameEnd, inPoint, outPoint, playing, fps.
    """
    return client.eval_mu(
        r'{ require commands;'
        r' "{\"frame\":" + string(frame())'
        r' + ",\"frameStart\":" + string(frameStart())'
        r' + ",\"frameEnd\":" + string(frameEnd())'
        r' + ",\"inPoint\":" + string(inPoint())'
        r' + ",\"outPoint\":" + string(outPoint())'
        r' + ",\"playing\":" + (if isPlaying() then "true" else "false")'
        r' + ",\"fps\":" + string(fps())'
        r' + "}";'
        r' }'
    )


@mcp.tool()
def set_playback_speed(direction: int = 1) -> str:
    """Set the playback increment (direction and speed).

    Args:
        direction: Positive for forward, negative for reverse.
                   1 = normal forward, -1 = normal reverse,
                   2 = 2x forward, etc.
    """
    return client.eval_mu(
        f'{{ require commands; setInc({direction}); string(inc()); }}'
    )
