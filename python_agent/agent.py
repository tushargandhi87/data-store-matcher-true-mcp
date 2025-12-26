"""Main Python Agent for ACAT Datastore Matching - Pattern 2 (Agentic)."""
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    CLAUDE_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_TEMPERATURE,
    USER_INPUT_FILE, OUTPUT_DIR, RATE_LIMIT_DELAY, LOG_LEVEL
)
from mcp_client_wrapper import MCPClientWrapper
from agentic_orchestrator import AgenticOrchestrator
from excel_writer import ExcelWriter

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('agent.log'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def load_user_input(filepath: Path) -> List[str]:
    """Load user datastores from Excel file."""
    try:
        logger.info(f"Loading user input from: {filepath}")
        df = pd.read_excel(filepath)
        column_name = df.columns[0]
        datastores = df[column_name].dropna().tolist()
        datastores = [str(ds).strip() for ds in datastores if str(ds).strip()]
        logger.info(f"Loaded {len(datastores)} user datastores")
        return datastores
    except Exception as e:
        logger.error(f"Error loading user input: {e}", exc_info=True)
        raise


def print_summary(results: List[Dict[str, Any]]):
    """Print summary statistics."""
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    
    total_matches = len(results)
    high_confidence = len([r for r in results if r.get("confidence", 0) >= 0.8])
    medium_confidence = len([r for r in results if 0.6 <= r.get("confidence", 0) < 0.8])
    low_confidence = len([r for r in results if r.get("confidence", 0) < 0.6])
    
    with_eol = len([r for r in results if r.get("eol_data") is not None])
    
    print(f"\nMATCHING RESULTS:")
    print(f"  Total datastores processed: {total_matches}")
    print(f"  High confidence (>=0.8): {high_confidence}")
    print(f"  Medium confidence (0.6-0.8): {medium_confidence}")
    print(f"  Low confidence (<0.6): {low_confidence}")
    print(f"\nEOL ENRICHMENT:")
    print(f"  Datastores with EOL data: {with_eol}")
    
    print("\n" + "="*60)


async def main():
    """Main agent execution - Pattern 2 (Agentic)."""
    try:
        print("\n" + "="*60)
        print("ACAT DATASTORE MATCHER - AGENTIC MODE (Pattern 2)")
        print("="*60 + "\n")
        
        logger.info("Initializing components...")
        
        # Initialize MCP client
        mcp_server_path = Path(__file__).parent.parent / "mcp_server" / "server.py"
        mcp_client = MCPClientWrapper(str(mcp_server_path))
        
        # Initialize agentic orchestrator
        orchestrator = AgenticOrchestrator(
            api_key=CLAUDE_API_KEY,
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=CLAUDE_TEMPERATURE
        )
        
        # Initialize Excel writer
        excel_writer = ExcelWriter(OUTPUT_DIR)
        
        logger.info("Connecting to MCP server...")
        await mcp_client.connect()
        
        # Load user input
        user_datastores = load_user_input(USER_INPUT_FILE)
        print(f"Loaded {len(user_datastores)} user datastores\n")
        
        # Fetch MCP tool schemas
        logger.info("Fetching MCP tool schemas...")
        mcp_tools = await mcp_client.list_tools()
        print(f"Available MCP tools: {[t['name'] for t in mcp_tools]}\n")
        
        print("="*60)
        print("AGENTIC PROCESSING - Claude Controls Workflow")
        print("="*60 + "\n")
        
        print("Starting agentic loop...")
        print("Claude will:")
        print("  1. Fetch ACAT reference data (via MCP tool)")
        print("  2. Match each datastore against reference")
        print("  3. Look up EOL data for low-confidence matches")
        print("  4. Return structured results\n")
        
        # Run agentic loop - Claude decides which tools to call!
        result = await orchestrator.run_agentic_loop(
            user_datastores=user_datastores,
            mcp_tools=mcp_tools,
            mcp_client=mcp_client,
            max_iterations=20
        )
        
        logger.info(f"Agentic loop completed with status: {result.get('status')}")
        
        if result["status"] == "success":
            results = result["results"]
            print(f"\n[OK] Agentic processing complete! Processed {len(results)} datastores\n")
            
            # Convert to expected format for Excel writer
            match_results = []
            eol_success = []
            eol_not_found = []
            eol_errors = []
            
            for item in results:
                # Match result
                match_results.append({
                    "input_datastore": item.get("input_datastore", ""),
                    "matched_datastore": item.get("matched_datastore", ""),
                    "confidence": item.get("confidence", 0.0),
                    "reasoning": item.get("reasoning", "")
                })
                
                # EOL data categorization
                eol_data = item.get("eol_data")
                if eol_data:
                    if eol_data.get("status") == "success":
                        eol_success.append({
                            "input_datastore": item.get("input_datastore"),
                            **eol_data
                        })
                    elif eol_data.get("status") == "not_found":
                        eol_not_found.append({
                            "input_datastore": item.get("input_datastore"),
                            **eol_data
                        })
                    elif eol_data.get("status") == "error":
                        eol_errors.append({
                            "input_datastore": item.get("input_datastore"),
                            **eol_data
                        })
            
            # Write output files
            print("Writing results to Excel...")
            match_file = excel_writer.write_match_results(match_results)
            print(f"[OK] Match results: {match_file}")
            
            if eol_success:
                success_file = excel_writer.write_eol_success(eol_success)
                print(f"[OK] EOL success: {success_file}")
            
            if eol_not_found:
                not_found_file = excel_writer.write_eol_not_found(eol_not_found)
                print(f"[OK] EOL not found: {not_found_file}")
            
            if eol_errors:
                error_file = excel_writer.write_eol_errors(eol_errors)
                print(f"[OK] EOL errors: {error_file}")
            
            # Print summary
            print_summary(results)
            
        else:
            print(f"\n[X] Agentic processing failed: {result.get('error')}")
            if "raw_response" in result:
                print(f"Raw response: {result['raw_response'][:500]}...")
        
        logger.info("Cleaning up...")
        await mcp_client.close()
        
        print("\n[OK] Processing complete!\n")
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        print("\n\nProcessing interrupted.\n")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        print(f"\n\nERROR: {e}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
