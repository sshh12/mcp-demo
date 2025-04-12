import json
import logging
import queue
import uuid
import base64
import requests
from typing import Dict
from urllib.parse import quote

from flask import Flask, Response, request, send_from_directory

_ENDPOINT = "/messages/"
_sessions = {}
_handlers = {}
_logger = logging.getLogger(__name__)

app = Flask(__name__)

# Serve static files from the frontend directory
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_frontend(path):
  return send_from_directory('../frontend', path)


class InvalidParams(Exception):
  pass


class MCPSession:
  def __init__(self, session_id: str):
    self.session_id = session_id
    self.queue = queue.Queue()
    self.server_name = "Demo MCP"
    self.server_version = "1.0.0"
    self.configured_tools = []


def on_mcp(method: str):
  """Decorator to register MCP method handlers."""

  def decorator(f):
    _handlers[method] = f
    return f

  return decorator


@on_mcp("initialize")
def on_initialize(session: MCPSession, params: Dict) -> Dict:
  version = params["protocolVersion"]
  if version != "2024-11-05":
    logging.warning(f"Using unknown version... this might not work: {version}")

  return {
    "protocolVersion": version,
    "capabilities": {
      "logging": {},
      "prompts": {},
      "resources": {"listChanged": True},
      "tools": {"listChanged": True},
    },
    "serverInfo": {"name": session.server_name, "version": session.server_version},
  }


@on_mcp("notifications/initialized")
def on_notifications_initialized(session: MCPSession, params: Dict) -> Dict:
  return {}


@on_mcp("tools/list")
def on_tools_list(session: MCPSession, params: Dict) -> Dict:
  """Return list of available tools."""
  return {
    "tools": [
      {
        "name": tool["name"],
        "description": tool["description"],
        "inputSchema": tool["inputSchema"],
      }
      for tool in session.configured_tools
    ]
  }


@on_mcp("tools/call")
def on_tools_call(session: MCPSession, params: Dict) -> Dict:
  """Handle tool execution requests."""
  tool_name = params["name"]
  tool_arguments = params["arguments"]

  # Check if we have configured tools
  for tool in session.configured_tools:
    if tool["name"] == tool_name and "endpoint" in tool:
      try:
        # Make an actual HTTP POST request to the tool's endpoint
        response = requests.post(
          tool["endpoint"],
          json=tool_arguments,
          headers={"Content-Type": "application/json"},
          timeout=30
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        # Return the response text
        return {
          "content": [
            {
              "type": "text", 
              "text": response.text
            }
          ],
          "isError": False,
        }
      except requests.RequestException as e:
        return {
          "content": [{"type": "text", "text": f"Error calling tool endpoint: {str(e)}"}],
          "isError": True,
        }

  # If no configured tools match, return an error
  return {
    "content": [
      {
        "type": "text",
        "text": f"No tool found with name: {tool_name}",
      }
    ],
    "isError": True,
  }


@on_mcp("resources/list")
def on_resources_list(session: MCPSession, params: Dict) -> Dict:
  return {"resources": []}


@on_mcp("resources/templates/list")
def on_resources_templates_list(session: MCPSession, params: Dict) -> Dict:
  """Return an empty list of resource templates."""
  return {"resourceTemplates": []}


def _serve_sse(config_b64=None):
  session_uuid = uuid.uuid4()
  session = MCPSession(session_uuid)
  _sessions[session_uuid] = session
  
  # Check if config parameter is present
  if config_b64:
    try:
      # Decode base64 config
      config_json = base64.b64decode(config_b64).decode('utf-8')
      config = json.loads(config_json)
      
      # Update session with server info if provided
      if "serverInfo" in config:
        server_info = config.get("serverInfo", {})
        session.server_name = server_info.get("name", "Demo MCP")
        session.server_version = server_info.get("version", "1.0.0")
      
      # Store tools if provided
      if "tools" in config:
        session.configured_tools = config.get("tools", [])
      
      _logger.info(f"Configured session with: {config}")
    except Exception as e:
      _logger.error(f"Error parsing config: {e}")
  
  session_uri = f"{quote(_ENDPOINT)}?session_id={session_uuid.hex}"
  yield f"event: endpoint\ndata: {session_uri}\n\n"

  while True:
    try:
      message = session.queue.get(timeout=10.0)
      _logger.debug(f"Sending message: {message}")
      yield f"data: {json.dumps(message)}\n\n"
    except queue.Empty:
      ping = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "ping"}
      yield f"data: {json.dumps(ping)}\n\n"
    except Exception as e:
      _logger.error(f"SSE worker error: {e}")
      break


@app.route("/sse", methods=["GET"])
def sse():
  """SSE endpoint that clients connect to."""
  # Get config from request
  config_b64 = request.args.get("config")
  
  return Response(
    _serve_sse(config_b64),
    mimetype="text/event-stream",
    headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
  )


@app.route("/messages/", methods=["POST"])
def on_message():
  """Handle incoming messages from clients."""
  session_id = request.args.get("session_id")
  if not session_id:
    return {"error": "No session_id provided"}, 400

  try:
    session_id = uuid.UUID(session_id)
    session = _sessions.get(session_id)
  except ValueError:
    _logger.error(f"Invalid session_id format: {session_id}")
    return {"error": "Invalid session_id format"}, 400

  if not session:
    _logger.error(f"Session {session_id} not found")
    return {"error": "Invalid session_id"}, 404

  req_json = request.get_json()
  method = req_json.get("method")
  params = req_json.get("params", {})

  _logger.debug(f"Received message: {req_json}")
  if not method:
    return {}

  try:
    handler = _handlers[method]
  except KeyError:
    _logger.error(f"Method {method} called by client but not implemented")
    return {"error": f"Method {method} not found"}, 404

  try:
    resp = {"result": handler(session, params)}
  except InvalidParams as e:
    resp = {"error": {"code": -32603, "message": str(e)}}
  except Exception as e:
    _logger.error(f"Error in handler {method}: {e}")
    return {"error": str(e)}, 500

  if req_json.get("id") is not None:
    session.queue.put({"jsonrpc": "2.0", "id": req_json.get("id"), **resp})

  return {}
