"""Tool 1: get_acat_reference - Load ACAT reference datastore names."""
import logging
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

logger = logging.getLogger(__name__)


class ACATReferenceCache:
    """Cache for ACAT reference data to avoid reloading on every call."""
    
    def __init__(self):
        self._reference_list: List[str] = []
        self._loaded = False
    
    def load(self, filepath: Path) -> Dict[str, Any]:
        """Load ACAT reference data from Excel file.
        
        Args:
            filepath: Path to ACAT_Data_Stores_Master.xlsx
            
        Returns:
            Dictionary with reference_list and total_count
        """
        if self._loaded:
            logger.info("Returning cached ACAT reference data")
            return {
                "reference_list": self._reference_list,
                "total_count": len(self._reference_list)
            }
        
        try:
            if not filepath.exists():
                return {
                    "status": "error",
                    "error_type": "FILE_NOT_FOUND",
                    "error_message": f"ACAT reference file not found: {filepath}",
                    "reference_list": [],
                    "total_count": 0
                }
            
            logger.info(f"Loading ACAT reference from: {filepath}")
            
            # Load Excel file
            df = pd.read_excel(filepath)
            
            # Extract datastore names from appropriate column
            # Assuming the column is named "Datastore" or first column
            if "Datastore" in df.columns:
                column_name = "Datastore"
            elif "datastore" in df.columns:
                column_name = "datastore"
            else:
                # Use first column
                column_name = df.columns[0]
            
            # Extract unique non-null values
            datastores = df[column_name].dropna().unique().tolist()
            
            # Convert to strings and sort
            self._reference_list = sorted([str(ds).strip() for ds in datastores if str(ds).strip()])
            self._loaded = True
            
            logger.info(f"Loaded {len(self._reference_list)} ACAT reference datastores")
            
            return {
                "reference_list": self._reference_list,
                "total_count": len(self._reference_list)
            }
            
        except Exception as e:
            logger.error(f"Error loading ACAT reference: {e}", exc_info=True)
            return {
                "status": "error",
                "error_type": "LOAD_ERROR",
                "error_message": f"Failed to load ACAT reference: {str(e)}",
                "reference_list": [],
                "total_count": 0
            }


# Global cache instance
_acat_cache = ACATReferenceCache()


def get_acat_reference(filepath: Path) -> Dict[str, Any]:
    """Get ACAT reference datastore names.
    
    This function is called by the MCP server tool handler.
    
    Args:
        filepath: Path to ACAT reference Excel file
        
    Returns:
        Dictionary with reference_list and total_count
    """
    return _acat_cache.load(filepath)
