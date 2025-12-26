"""Main Python Agent for ACAT Datastore Matching."""
import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    CLAUDE_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_TEMPERATURE,
    USER_INPUT_FILE, OUTPUT_DIR, CONFIDENCE_THRESHOLD, RATE_LIMIT_DELAY, LOG_LEVEL
)
from mcp_client_wrapper import MCPClientWrapper
from llm_matcher import LLMatcher
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


def extract_product_version(datastore_name: str) -> Tuple[str, str]:
    """Extract product name and version from datastore string."""
    cleaned = re.sub(r'\s+(Enterprise|Standard|Express|Developer|SP\d+|R\d+).*$', '', datastore_name, flags=re.IGNORECASE)
    match = re.match(r'^(.+?)\s+([\d.]+.*?)$', cleaned)
    
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    return datastore_name, ""


def print_summary(match_results: List[Dict[str, Any]], eol_results: List[Dict[str, Any]]):
    """Print summary statistics."""
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    
    total_matches = len(match_results)
    high_confidence = len([r for r in match_results if r.get("confidence", 0) >= 0.8])
    medium_confidence = len([r for r in match_results if 0.6 <= r.get("confidence", 0) < 0.8])
    low_confidence = len([r for r in match_results if r.get("confidence", 0) < 0.6])
    
    print(f"\nMATCHING RESULTS:")
    print(f"  Total datastores processed: {total_matches}")
    print(f"  High confidence (>=0.8): {high_confidence}")
    print(f"  Medium confidence (0.6-0.8): {medium_confidence}")
    print(f"  Low confidence (<0.6): {low_confidence}")
    
    total_eol_lookups = len(eol_results)
    success = len([r for r in eol_results if r.get("status") == "success"])
    not_found = len([r for r in eol_results if r.get("status") == "not_found"])
    errors = len([r for r in eol_results if r.get("status") == "error"])
    
    print(f"\nEOL LOOKUP RESULTS:")
    print(f"  Total lookups: {total_eol_lookups}")
    print(f"  Successful: {success}")
    print(f"  Not found: {not_found}")
    print(f"  Errors: {errors}")
    
    print("\n" + "="*60)


async def main():
    """Main agent execution."""
    try:
        print("\n" + "="*60)
        print("ACAT DATASTORE MATCHER - MCP AGENT")
        print("="*60 + "\n")
        
        logger.info("Initializing components...")
        
        mcp_server_path = Path(__file__).parent.parent / "mcp_server" / "server.py"
        mcp_client = MCPClientWrapper(str(mcp_server_path))
        
        llm_matcher = LLMatcher(
            api_key=CLAUDE_API_KEY,
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=CLAUDE_TEMPERATURE
        )
        
        excel_writer = ExcelWriter(OUTPUT_DIR)
        
        logger.info("Connecting to MCP server...")
        await mcp_client.connect()
        
        user_datastores = load_user_input(USER_INPUT_FILE)
        print(f"Loaded {len(user_datastores)} user datastores\n")
        
        logger.info("Fetching ACAT reference data...")
        acat_response = await mcp_client.call_tool("get_acat_reference", {})
        
        if "error_type" in acat_response:
            logger.error(f"Failed to get ACAT reference: {acat_response['error_message']}")
            print(f"ERROR: {acat_response['error_message']}")
            return
        
        reference_list = acat_response.get("reference_list", [])
        total_count = acat_response.get("total_count", 0)
        
        print(f"Retrieved {total_count} ACAT reference datastores\n")
        logger.info(f"ACAT reference loaded: {total_count} entries")
        
        print("="*60)
        print("PHASE 1: LLM MATCHING")
        print("="*60 + "\n")
        
        match_results = []
        
        for i, datastore in enumerate(user_datastores, 1):
            print(f"[{i}/{len(user_datastores)}] Matching: {datastore}")
            
            result = await llm_matcher.match(datastore, reference_list)
            match_results.append(result)
            
            print(f"  -> {result['matched_datastore']} (confidence: {result['confidence']:.2f})")
            print(f"  -> Reasoning: {result['reasoning']}\n")
            
            await asyncio.sleep(RATE_LIMIT_DELAY)
        
        print("\nWriting match results...")
        match_file = excel_writer.write_match_results(match_results)
        print(f"[OK] Saved to: {match_file}\n")
        
        print("="*60)
        print("PHASE 2: EOL INFORMATION LOOKUP")
        print("="*60 + "\n")
        
        low_confidence_matches = [r for r in match_results if r.get("confidence", 1.0) < CONFIDENCE_THRESHOLD]
        
        print(f"Found {len(low_confidence_matches)} low-confidence matches requiring EOL lookup\n")
        
        eol_results = []
        
        for i, match in enumerate(low_confidence_matches, 1):
            input_ds = match["input_datastore"]
            matched_ds = match["matched_datastore"]
            
            print(f"[{i}/{len(low_confidence_matches)}] Looking up: {input_ds}")
            
            if matched_ds and matched_ds != "NOT FOUND" and matched_ds != "ERROR":
                product, version = extract_product_version(matched_ds)
            else:
                product, version = extract_product_version(input_ds)
            
            if not version:
                print(f"  -> Skipping: No version found\n")
                continue
            
            print(f"  -> Product: {product}, Version: {version}")
            
            eol_result = await mcp_client.call_tool("endoflife_lookup", {
                "product": product,
                "version": version
            })
            
            eol_result["input_datastore"] = input_ds
            eol_results.append(eol_result)
            
            status = eol_result.get("status", "unknown")
            if status == "success":
                print(f"  [OK] Found: {eol_result.get('matched_version')} (EOL: {eol_result.get('eol_date')})")
            elif status == "not_found":
                print(f"  [X] Not found: {eol_result.get('error_message')}")
            else:
                print(f"  [X] Error: {eol_result.get('error_message')}")
            
            print()
            
            await asyncio.sleep(RATE_LIMIT_DELAY)
        
        success_results = [r for r in eol_results if r.get("status") == "success"]
        not_found_results = [r for r in eol_results if r.get("status") == "not_found"]
        error_results = [r for r in eol_results if r.get("status") == "error"]
        
        print("Writing EOL lookup results...")
        
        if success_results:
            success_file = excel_writer.write_eol_success(success_results)
            print(f"[OK] Success results: {success_file}")
        else:
            print("  (No success results)")
        
        if not_found_results:
            not_found_file = excel_writer.write_eol_not_found(not_found_results)
            print(f"[OK] Not found results: {not_found_file}")
        else:
            print("  (No not found results)")
        
        if error_results:
            error_file = excel_writer.write_eol_errors(error_results)
            print(f"[OK] Error results: {error_file}")
        else:
            print("  (No error results)")
        
        print_summary(match_results, eol_results)
        
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
