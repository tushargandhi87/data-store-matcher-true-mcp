# Quick Start Guide

## Initial Setup (5 minutes)

1. **Run setup script**:
   ```bash
   python setup.py
   ```

2. **Configure API key**:
   Edit `.env` file:
   ```
   CLAUDE_API_KEY=sk-ant-your-actual-key-here
   ```

3. **Add ACAT reference data**:
   Place your ACAT master file in:
   ```
   mcp_server/data/ACAT_Data_Stores_Master.xlsx
   ```

4. **Add your input data**:
   Place your datastore list in:
   ```
   input/user_input.xlsx
   ```
   (Or use `input/test_user_input.xlsx` for testing)

## Running the Agent

```bash
cd python_agent
python agent.py
```

## Expected Results

The agent will:
1. Connect to MCP server ✓
2. Load ACAT reference (449 entries) ✓
3. Match each input datastore using LLM ✓
4. Look up EOL info for low-confidence matches ✓
5. Generate 4 Excel output files ✓

## Output Files

Check `output/` directory:
- `datastore_match_results.xlsx` - All matches with confidence scores
- `api_success.xlsx` - Successful EOL lookups
- `api_not_found.xlsx` - Products not found in endoflife.date
- `api_errors.xlsx` - API errors (if any)

## Troubleshooting

**Problem**: `ModuleNotFoundError: No module named 'mcp'`
- **Fix**: Run `pip install -r requirements.txt`

**Problem**: `Failed to connect to MCP server`
- **Fix**: Check that `mcp_server/server.py` exists

**Problem**: `ACAT reference file not found`
- **Fix**: Verify file is in `mcp_server/data/ACAT_Data_Stores_Master.xlsx`

**Problem**: `Authentication error` (Claude API)
- **Fix**: Check your `CLAUDE_API_KEY` in `.env`

For more help, see full `README.md`
