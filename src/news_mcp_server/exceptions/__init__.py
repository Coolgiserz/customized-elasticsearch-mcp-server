class MCPException(Exception):
    """MCP 自定义基础异常"""
    pass


class ResourceException(MCPException):
    """资源未找到异常"""
    pass


class ToolException(MCPException):
    """资源未找到异常"""
    pass