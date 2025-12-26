"""LLM Matcher using Claude API for fuzzy datastore matching."""
import logging
import json
from typing import Dict, Any, List
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class LLMatcher:
    """Use Claude API for fuzzy datastore name matching."""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", max_tokens: int = 1000, temperature: float = 0.1):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
    def build_prompt(self, input_datastore: str, reference_list: List[str]) -> str:
        """Build matching prompt for Claude."""
        formatted_ref = "\n".join([f"- {ds}" for ds in reference_list])
        
        prompt = f"""TASK: Match the input datastore to the most appropriate ACAT reference value.

INPUT DATASTORE: {input_datastore}

ACAT REFERENCE LIST:
{formatted_ref}

MATCHING RULES:
1. Handle typos: "PostGres" → "PostgreSQL"
2. Ignore case: "mysql" = "MySQL"
3. Ignore special chars: "PostGres: 14.6" = "PostgreSQL 14.6"
4. Match closest version if exact not found
5. Product name MUST match (PostgreSQL ≠ MySQL)
6. NEVER match different products
7. Strip version suffixes: ".x", "x", "-log"
8. Ignore qualifiers: "SP2", "R2", "Enterprise" unless in reference

Provide confidence score 0.0-1.0:
- 1.0 = Exact match
- 0.8-0.95 = Very confident (minor differences)
- 0.6-0.75 = Moderate confidence (unclear version)
- < 0.6 = Low confidence (product unclear or not in list)

OUTPUT FORMAT (JSON only, no other text):
{{
  "matched_datastore": "exact reference name from list or 'NOT FOUND'",
  "confidence": 0.95,
  "reasoning": "brief explanation of match"
}}"""
        
        return prompt
    
    async def match(self, input_datastore: str, reference_list: List[str]) -> Dict[str, Any]:
        """Match input datastore to ACAT reference using LLM."""
        try:
            logger.info(f"Matching datastore: {input_datastore}")
            
            prompt = self.build_prompt(input_datastore, reference_list)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            logger.debug(f"Claude response: {response_text}")
            
            try:
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                result = json.loads(response_text)
                
                if "matched_datastore" not in result or "confidence" not in result:
                    raise ValueError("Missing required fields in response")
                
                result["input_datastore"] = input_datastore
                
                logger.info(f"Match result: {result['matched_datastore']} (confidence: {result['confidence']})")
                
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse Claude response: {e}")
                return {
                    "input_datastore": input_datastore,
                    "matched_datastore": "NOT FOUND",
                    "confidence": 0.0,
                    "reasoning": f"Failed to parse LLM response: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error in LLM matching: {e}", exc_info=True)
            return {
                "input_datastore": input_datastore,
                "matched_datastore": "ERROR",
                "confidence": 0.0,
                "reasoning": f"Error during matching: {str(e)}"
            }
