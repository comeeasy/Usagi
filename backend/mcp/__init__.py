"""
mcp/__init__.py — FastMCP 인스턴스 생성 및 export

FastMCP 서버는 SSE (Server-Sent Events) transport로 동작한다.
tools.py에서 @mcp.tool() 데코레이터로 도구를 등록한다.
main.py에서 app.mount("/mcp", mcp_app) 형태로 FastAPI 앱에 마운트한다.
"""

# TODO: FastMCP 인스턴스 초기화
# from fastmcp import FastMCP
# mcp = FastMCP("Ontology Platform MCP Server")
# from mcp import tools  # 도구 등록 (side effect import)
# mcp_app = mcp.get_asgi_app()  # SSE ASGI 앱 생성
