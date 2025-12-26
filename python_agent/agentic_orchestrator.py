"""Agentic Orchestrator - LLM-driven tool selection (Pattern 2)."""
import logging
import json
from typing import List, Dict, Any, Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class AgenticOrchestrator:
    """
    Implements Pattern 2: LLM-driven agentic workflow.
    Claude decides which MCP tools to call based on their descriptions.
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", 
                 max_tokens: int = 4000, temperature: float = 0.1):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
    def convert_mcp_tools_to_claude(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert MCP tool schemas to Claude Anthropic tool format.
        
        MCP format: {"name": "...", "description": "...", "inputSchema": {...}}
        Claude format: {"name": "...", "description": "...", "input_schema": {...}}
        """
        claude_tools = []
        for tool in mcp_tools:
            claude_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}})
            }
            claude_tools.append(claude_tool)
        
        logger.info(f"Converted {len(claude_tools)} MCP tools to Claude format")
        return claude_tools
    
    def build_system_prompt(self) -> str:
        """Build system prompt for the agentic orchestrator."""
        return """You are an intelligent datastore matching agent with access to MCP tools.

Your task is to match user-provided datastore names against ACAT reference data and enrich low-confidence matches with EOL information.

WORKFLOW STRATEGY:
1. First, call get_acat_reference to retrieve the ACAT reference list (call this ONCE)
2. For each user datastore, compare it against the ACAT reference list
3. Return a match with confidence score (0.0-1.0) and reasoning
4. For matches with confidence < 0.7, call endoflife_lookup to get version/EOL data

MATCHING RULES:
- Handle typos: "PostGres" → "PostgreSQL"
- Ignore case: "mysql" = "MySQL"  
- Match closest version if exact not found
- Product name MUST match (PostgreSQL ≠ MySQL)
- Strip version suffixes: ".x", "x", "-log"
- Provide confidence: 1.0 = exact, 0.8-0.95 = very close, 0.6-0.75 = moderate, < 0.6 = uncertain

RESPONSE FORMAT:
When you have processed all datastores, return a JSON array with this structure:
```json
[
  {
    "input_datastore": "PostgreSQL 14",
    "matched_datastore": "PostgreSQL 14",
    "confidence": 1.0,
    "reasoning": "Exact match",
    "eol_data": null or {...}
  }
]
```

Use tools strategically and provide final results when complete."""

    async def run_agentic_loop(
        self, 
        user_datastores: List[str], 
        mcp_tools: List[Dict[str, Any]],
        mcp_client,
        max_iterations: int = 20
    ) -> Dict[str, Any]:
        """
        Run the agentic loop where Claude decides which tools to call.
        
        Args:
            user_datastores: List of datastore names to match
            mcp_tools: MCP tool schemas (will be converted to Claude format)
            mcp_client: MCP client for executing tool calls
            max_iterations: Maximum number of agent iterations
            
        Returns:
            Dict with final results or error
        """
        logger.info(f"Starting agentic loop for {len(user_datastores)} datastores")
        
        # Convert tools to Claude format
        claude_tools = self.convert_mcp_tools_to_claude(mcp_tools)
        
        # Build user prompt with the task
        user_prompt = f"""Match the following {len(user_datastores)} datastore names against ACAT reference data:

{chr(10).join([f"{i+1}. {ds}" for i, ds in enumerate(user_datastores)])}

Use the available tools to:
1. Get ACAT reference data
2. Match each datastore
3. Look up EOL information for low-confidence matches (< 0.7)

Provide structured results for all datastores when complete."""

        # Initialize conversation
        messages = [{"role": "user", "content": user_prompt}]
        
        # Agentic loop
        for iteration in range(max_iterations):
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")
            
            try:
                # Call Claude with tools
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=self.build_system_prompt(),
                    messages=messages,
                    tools=claude_tools
                )
                
                logger.debug(f"Claude response stop_reason: {response.stop_reason}")
                
                # Add assistant response to conversation
                assistant_message = {"role": "assistant", "content": response.content}
                messages.append(assistant_message)
                
                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Claude finished - extract final answer
                    logger.info("Claude finished (end_turn)")
                    return self._extract_final_answer(response.content)
                
                elif response.stop_reason == "tool_use":
                    # Claude wants to use tools
                    tool_results = []
                    
                    for content_block in response.content:
                        if content_block.type == "tool_use":
                            tool_name = content_block.name
                            tool_input = content_block.input
                            tool_use_id = content_block.id
                            
                            logger.info(f"Claude requested tool: {tool_name} with input: {tool_input}")
                            
                            # Execute tool via MCP client
                            tool_result = await mcp_client.call_tool(tool_name, tool_input)
                            
                            logger.info(f"Tool {tool_name} returned: {type(tool_result)}")
                            
                            # Format tool result for Claude
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": json.dumps(tool_result)
                            })
                    
                    # Add tool results to conversation
                    messages.append({"role": "user", "content": tool_results})
                    
                else:
                    logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
                    return {
                        "status": "error",
                        "error": f"Unexpected stop reason: {response.stop_reason}",
                        "results": []
                    }
                    
            except Exception as e:
                logger.error(f"Error in agentic loop iteration {iteration + 1}: {e}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                    "results": []
                }
        
        # Max iterations reached
        logger.warning(f"Max iterations ({max_iterations}) reached without completion")
        return {
            "status": "incomplete",
            "error": "Max iterations reached",
            "results": []
        }
    
    def _extract_final_answer(self, content_blocks: List) -> Dict[str, Any]:
        """Extract final answer from Claude's response."""
        for block in content_blocks:
            if block.type == "text":
                text = block.text
                
                # Try to extract JSON from response
                try:
                    # Look for JSON array in markdown code blocks or plain text
                    if "```json" in text:
                        json_start = text.find("```json") + 7
                        json_end = text.find("```", json_start)
                        json_text = text[json_start:json_end].strip()
                    elif "```" in text:
                        json_start = text.find("```") + 3
                        json_end = text.find("```", json_start)
                        json_text = text[json_start:json_end].strip()
                    else:
                        # Try to find JSON array directly
                        json_text = text.strip()
                    
                    results = json.loads(json_text)
                    
                    if isinstance(results, list):
                        logger.info(f"Successfully extracted {len(results)} results")
                        return {
                            "status": "success",
                            "results": results
                        }
                    else:
                        logger.warning(f"Expected list, got {type(results)}")
                        return {
                            "status": "error",
                            "error": "Results not in expected format",
                            "raw_response": text
                        }
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {e}")
                    return {
                        "status": "error",
                        "error": f"JSON parse error: {e}",
                        "raw_response": text
                    }
        
        return {
            "status": "error", 
            "error": "No text content in response",
            "results": []
        }
