#!/usr/bin/env python3
"""
Google Gemini LLM Provider for MCP tool calling
"""

from typing import List, Dict, Any
from .base import LLMProvider
import copy

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiProvider(LLMProvider):
    """Google Gemini provider for MCP tool orchestration"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """Initialize Gemini provider"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed. Install with: pip install google-generativeai")
        
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        self.model_instance = genai.GenerativeModel(model)
        self.chat_session = None  # Will be created when needed

    def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int = 1024
    ) -> Any:
        """Call Gemini with tools"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔧 [Gemini] call_with_tools called with {len(messages)} messages")
        
        # Convert MCP tools to Gemini format
        gemini_tools = self._convert_tools_to_gemini(tools)
        
        # For first call, create chat session
        if self.chat_session is None:
            logger.info(f"🔧 [Gemini] Creating new chat session")
            self.chat_session = self.model_instance.start_chat(history=[])
        
        try:
            # Get the last message (only send the new message, not full history)
            last_message = messages[-1]
            logger.info(f"🔧 [Gemini] Last message: {last_message}")
            
            # Extract content based on message structure
            if isinstance(last_message, dict):
                # Check if it's a function response (parts format)
                if "parts" in last_message:
                    content = last_message["parts"]
                    logger.info(f"🔧 [Gemini] Sending function response parts")
                else:
                    content = last_message.get("content", "")
                    logger.info(f"🔧 [Gemini] Sending regular content")
            else:
                content = last_message
            
            logger.info(f"🔧 [Gemini] Sending content type: {type(content)}")
            
            # Send message
            response = self.chat_session.send_message(
                content,
                tools=gemini_tools,
                generation_config=genai.GenerationConfig(max_output_tokens=max_tokens)
            )
            logger.info(f"✅ [Gemini] Got response")
            return response
                
        except Exception as e:
            logger.error(f"❌ [Gemini] Error in call_with_tools: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _convert_tools_to_gemini(self, mcp_tools: List[Dict[str, Any]]) -> List:
        """Convert MCP tool format to Gemini function declarations"""
        from google.generativeai.types import FunctionDeclaration, Tool
        import copy
        
        function_declarations = []
        for tool in mcp_tools:
            # Deep copy to avoid modifying original
            input_schema = copy.deepcopy(tool["input_schema"])
            
            # Remove fields Gemini doesn't support
            fields_to_remove = ["additionalProperties", "$schema", "default"]
            for field in fields_to_remove:
                if field in input_schema:
                    del input_schema[field]
            
            # Clean nested properties recursively
            if "properties" in input_schema:
                for prop_key, prop_val in input_schema["properties"].items():
                    if isinstance(prop_val, dict):
                        for field in fields_to_remove:
                            if field in prop_val:
                                del prop_val[field]
            
            func_decl = FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=input_schema
            )
            function_declarations.append(func_decl)
        
        return [Tool(function_declarations=function_declarations)]
    
    def extract_text_content(self, response: Any) -> str:
        """Extract text from Gemini response"""
        try:
            if response.text:
                return response.text
        except:
            pass
        return ""
    
    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from Gemini response"""
        import logging
        logger = logging.getLogger(__name__)
        
        tool_calls = []
        
        try:
            if not hasattr(response, 'parts') or response.parts is None:
                logger.info(f"🔧 [Gemini] Response has no parts")
                return []
            
            for part in response.parts:
                # Check if part has function_call AND it's not None/empty
                if hasattr(part, 'function_call') and part.function_call is not None:
                    fc = part.function_call
                    
                    # Also check if args exists
                    if not hasattr(fc, 'args') or fc.args is None:
                        logger.info(f"🔧 [Gemini] Function call has no args, skipping")
                        continue
                    
                    # Convert function call arguments to dict
                    args_dict = dict(fc.args)
                    
                    tool_calls.append({
                        "id": fc.name,
                        "name": fc.name,
                        "input": args_dict
                    })
                    logger.info(f"🔧 [Gemini] Found tool call: {fc.name}")
        except Exception as e:
            logger.error(f"❌ [Gemini] Error extracting tool calls: {e}")
            return []
        
        return tool_calls
    
    def format_tool_result(self, tool_call_id: str, result: str) -> Dict[str, Any]:
        """Format tool result for Gemini"""
        # Gemini expects tool results as user messages with specific format
        return {
            "role": "user",
            "parts": [{
                "function_response": {
                    "name": tool_call_id,
                    "response": {"result": str(result)}
                }
            }]
        }
    
    def _convert_tools_to_gemini(self, mcp_tools: List[Dict[str, Any]]) -> List:
        """Convert MCP tool format to Gemini function declarations"""
        from google.generativeai.types import FunctionDeclaration, Tool
        import copy
        
        function_declarations = []
        for tool in mcp_tools:
            # Deep copy to avoid modifying original
            input_schema = copy.deepcopy(tool["input_schema"])
            
            # Remove fields Gemini doesn't support
            fields_to_remove = ["additionalProperties", "$schema", "default"]
            for field in fields_to_remove:
                if field in input_schema:
                    del input_schema[field]
            
            # Clean nested properties recursively
            if "properties" in input_schema:
                for prop_key, prop_val in input_schema["properties"].items():
                    if isinstance(prop_val, dict):
                        for field in fields_to_remove:
                            if field in prop_val:
                                del prop_val[field]
            
            func_decl = FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=input_schema
            )
            function_declarations.append(func_decl)
        
        return [Tool(function_declarations=function_declarations)]
    
    def extract_text_content(self, response: Any) -> str:
        """Extract text from Gemini response"""
        try:
            if response.text:
                return response.text
        except:
            pass
        return ""
    
    def format_tool_result(self, tool_call_id: str, result: str) -> Dict[str, Any]:
        """Format tool result for Gemini"""
        # Gemini expects just the parts for function responses
        return {
            "parts": [{
                "function_response": {
                    "name": tool_call_id,
                    "response": {"result": str(result)}
                }
            }]
        }