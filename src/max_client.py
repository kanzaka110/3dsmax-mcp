import json
import socket
import time
from typing import Any, Optional
from uuid import uuid4

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_TIMEOUT = 120.0


class MaxClient:
    """TCP socket client that sends commands to 3ds Max."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send_command(
        self,
        command: str,
        cmd_type: str = "maxscript",
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Send a command to 3ds Max via TCP and return the parsed JSON response."""
        effective_timeout = timeout or self.timeout
        request_id = uuid4().hex
        started_at = time.perf_counter()

        request = json.dumps({
            "command": command,
            "type": cmd_type,
            "requestId": request_id,
            "protocolVersion": 2,
        }, ensure_ascii=True)

        # Create socket and connect
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(effective_timeout)

        try:
            sock.connect((self.host, self.port))

            # Send request with newline delimiter
            sock.sendall((request + "\n").encode("utf-8"))

            # Receive response (read until newline)
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in response_data:
                    break

            # Strip UTF-8 BOM if present
            if response_data.startswith(b'\xef\xbb\xbf'):
                response_data = response_data[3:]
            response_str = response_data.decode("utf-8", errors="replace").strip()

            if not response_str:
                raise RuntimeError("Empty response from 3ds Max")

            response = json.loads(response_str)
            response_request_id = response.get("requestId")
            if response_request_id not in (None, "", request_id):
                raise RuntimeError(
                    f"Mismatched response requestId: expected {request_id}, got {response_request_id}"
                )

            response["requestId"] = request_id
            meta = response.get("meta")
            if not isinstance(meta, dict):
                meta = {}
                response["meta"] = meta
            meta.setdefault(
                "clientRoundTripMs",
                round((time.perf_counter() - started_at) * 1000.0, 3),
            )

            if not response.get("success", False):
                error_msg = response.get("error", "Unknown error")
                raise RuntimeError(f"MAXScript error: {error_msg}")

            return response

        except socket.timeout:
            raise TimeoutError(
                f"3ds Max did not respond within {effective_timeout}s. "
                "Is the MCP TCP listener running in 3ds Max?"
            )
        except ConnectionRefusedError:
            raise ConnectionError(
                f"Could not connect to 3ds Max on {self.host}:{self.port}. "
                "Is the MCP TCP listener running in 3ds Max?"
            )
        finally:
            sock.close()
