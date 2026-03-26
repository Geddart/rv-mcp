import atexit
import os
import socket
import threading
import time
from typing import Optional


DEFAULT_HOST = os.environ.get("RV_MCP_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("RV_MCP_PORT", "45124"))
DEFAULT_TIMEOUT = 30.0


class RvClient:
    """Persistent TCP client that speaks RV's native network protocol.

    RV must be running with the -network flag (default port 45125).
    Override with RV_MCP_HOST / RV_MCP_PORT env vars.
    Protocol based on RvCommunicator from rvNetwork.py, modernized for Python 3.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        name: str = "rv-mcp",
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.host = host
        self.port = port
        self.name = name
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._lock = threading.Lock()
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        """atexit handler — send DISCONNECT so RV doesn't reject future clients."""
        if self._connected:
            self.disconnect()

    def connect(self) -> None:
        """Connect to RV, send greeting, disable ping-pong."""
        # Always clean up any previous socket
        if self._sock:
            try:
                if self._connected:
                    self._send_message("DISCONNECT")
                self._sock.close()
            except OSError:
                pass
            self._sock = None
            self._connected = False

        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
        except ConnectionRefusedError:
            raise ConnectionError(
                f"Could not connect to RV on {self.host}:{self.port}. "
                "Is RV running with the -network flag?"
            )

        # Send greeting
        greeting = f"{self.name} rvController"
        self._send_raw(f"NEWGREETING {len(greeting)} {greeting}")

        # Disable heartbeat
        self._send_raw("PINGPONGCONTROL 1 0")

        self._connected = True

        # Wait for and consume RV's greeting response
        self._consume_greeting()

    def disconnect(self, send_msg: bool = True) -> None:
        """Disconnect from RV."""
        try:
            if send_msg and self._sock:
                self._send_message("DISCONNECT")
            if self._sock:
                self._sock.shutdown(socket.SHUT_RDWR)
                self._sock.close()
        except OSError:
            pass
        self._sock = None
        self._connected = False

    def _ensure_connected(self) -> None:
        """Auto-connect if not connected."""
        if not self._connected:
            self.connect()

    def _send_raw(self, data: str) -> None:
        """Send raw string as bytes."""
        self._sock.sendall(data.encode("utf-8"))

    def _send_message(self, content: str) -> None:
        """Send wrapped: MESSAGE <len> <content>"""
        encoded = content.encode("utf-8")
        header = f"MESSAGE {len(encoded)} ".encode("utf-8")
        self._sock.sendall(header + encoded)

    def _recv_bytes(self, n: int) -> bytes:
        """Receive exactly n bytes."""
        data = b""
        while len(data) < n:
            chunk = self._sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("RV closed the connection")
            data += chunk
        return data

    def _recv_field(self) -> bytes:
        """Read one space-delimited field from the socket."""
        field = b""
        while True:
            c = self._sock.recv(1)
            if not c:
                raise ConnectionError("RV closed the connection")
            if c == b" ":
                break
            field += c
        return field

    def _recv_single_message(self) -> tuple[str, bytes]:
        """Read one message: (type, content)."""
        msg_type = self._recv_field().decode("utf-8")
        msg_size = int(self._recv_field().decode("utf-8"))
        msg_content = self._recv_bytes(msg_size)
        return msg_type, msg_content

    def _consume_greeting(self) -> None:
        """Read and discard RV's greeting response after connecting."""
        try:
            msg_type, _content = self._recv_single_message()
            if msg_type not in ("GREETING", "NEWGREETING"):
                pass  # unexpected but not fatal
        except (socket.timeout, ConnectionError):
            pass  # RV may not always send a greeting

    def _wait_for_return(self) -> str:
        """Read messages until a RETURN value is received."""
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._sock.settimeout(remaining)

            msg_type, msg_content = self._recv_single_message()

            if msg_type == "MESSAGE":
                content_str = msg_content.decode("utf-8")
                parts = content_str.split(" ", 1)
                inner_type = parts[0]

                if inner_type == "RETURN":
                    return parts[1] if len(parts) > 1 else ""
                # Ignore other message contents (EVENTs, etc.)

            elif msg_type == "PING":
                self._send_raw("PONG 1 p")

            elif msg_type in ("GREETING", "NEWGREETING", "PONG"):
                pass  # ignore

        raise TimeoutError(
            f"RV did not return a value within {self.timeout}s. "
            "The Mu code may be too slow or RV is unresponsive."
        )

    @staticmethod
    def _strip_mu_quotes(value: str) -> str:
        """Strip outer Mu string quotes and unescape a return value.

        Mu wraps string return values in double quotes and escapes inner
        quotes with backslashes (e.g. '"{\\\"key\\\":1}"' for {"key":1}).
        This strips the outer quotes and unescapes so callers get clean values.
        """
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            inner = value[1:-1]
            return inner.replace('\\"', '"').replace('\\\\', '\\')
        return value

    def eval_mu(self, code: str) -> str:
        """Send Mu code via remote-eval and wait for the result string.

        Mu string quotes are automatically stripped from the return value.
        """
        with self._lock:
            self._ensure_connected()
            try:
                event = f"RETURNEVENT remote-eval * {code}"
                self._send_message(event)
                raw = self._wait_for_return()
                return self._strip_mu_quotes(raw)
            except (ConnectionError, ConnectionAbortedError, OSError) as exc:
                self._connected = False
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
                raise ConnectionError(
                    f"Lost connection to RV: {exc}. "
                    "Is RV still running with -network?"
                ) from exc

    def eval_mu_no_return(self, code: str) -> None:
        """Fire-and-forget Mu eval (no return value)."""
        with self._lock:
            self._ensure_connected()
            try:
                event = f"EVENT remote-eval * {code}"
                self._send_message(event)
            except (ConnectionError, ConnectionAbortedError, OSError) as exc:
                self._connected = False
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
                raise ConnectionError(
                    f"Lost connection to RV: {exc}. "
                    "Is RV still running with -network?"
                ) from exc


def escape_mu_string(s: str) -> str:
    """Escape a string for use inside Mu string literals.

    Normalizes Windows paths to forward slashes and escapes quotes.
    """
    return s.replace("\\", "/").replace('"', '\\"')
