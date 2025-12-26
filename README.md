# ACAT Datastore Matcher - MCP Implementation

An intelligent datastore name normalization system using Model Context Protocol (MCP) architecture with LLM-powered matching and End-of-Life information enrichment.

## 🎯 Overview

This system normalizes user-provided datastore names against ACAT reference data and enriches low-confidence matches with version and EOL information from endoflife.date API.

### Key Features

- **Pattern 2 (Agentic Orchestration)**: Tool descriptions guide agent workflow
- **LLM-Powered Matching**: Claude Sonnet 4 for intelligent fuzzy matching
- **Dual Agent Support**: Works with Claude Desktop and custom Python agent
- **Comprehensive Error Handling**: Graceful handling of edge cases
- **Rich Output**: 4 Excel files with formatted results

## 🏗️ Architecture

The system uses MCP (Model Context Protocol) with:
- **MCP Server**: 2 tools for data access (get_acat_reference, endoflife_lookup)
- **Python Agent**: Orchestrates workflow, performs LLM matching, writes output
- **Claude Desktop**: Alternative agent using same MCP server

### Workflow

**Phase 1: LLM Matching**
1. Agent calls `get_acat_reference` (once)
2. Agent performs LLM matching on each input
3. Results written to `datastore_match_results.xlsx`

**Phase 2: EOL Enrichment**
- For matches with confidence < 0.7:
  - Extract product/version
  - Call `endoflife_lookup` tool
  - Results categorized into 3 files

## 📁 Project Structure

```
datastore_matcher_mcp/
├── mcp_server/           # MCP server with 2 tools
│   ├── server.py
│   ├── tools/
│   │   ├── get_acat_reference.py
│   │   └── endoflife_lookup.py (50+ product mappings)
│   └── data/
│       └── ACAT_Data_Stores_Master.xlsx
├── python_agent/         # Custom Python agent
│   ├── agent.py
│   ├── mcp_client_wrapper.py
│   ├── llm_matcher.py
│   └── excel_writer.py
├── input/                # Your input files
│   └── user_input.xlsx
├── output/              # Generated outputs (4 Excel files)
├── .env                 # API keys (create from .env.example)
├── requirements.txt
└── README.md
```

## 🚀 Setup

### Prerequisites

- Python 3.10+
- Claude API key
- ACAT_Data_Stores_Master.xlsx file

### Installation

1. **Run setup script**:
   ```bash
   python setup.py
   ```

2. **Configure API key**:
   Copy `.env.example` to `.env` and add:
   ```
   CLAUDE_API_KEY=sk-ant-your-key-here
   ```

3. **Add data files**:
   - Place ACAT reference: `mcp_server/data/ACAT_Data_Stores_Master.xlsx`
   - Place your input: `input/user_input.xlsx`

## 📝 Usage

### Option 1: Python Agent

```bash
cd python_agent
python agent.py
```

**Output:**
- `output/datastore_match_results.xlsx` - All matches with confidence scores
- `output/api_success.xlsx` - Successful EOL lookups (11 columns)
- `output/api_not_found.xlsx` - Products not found (7 columns)
- `output/api_errors.xlsx` - API errors (8 columns)

### Option 2: Claude Desktop

1. Copy `claude_desktop/claude_desktop_config.json` to:
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Update paths in the config file

3. Restart Claude Desktop

4. Start conversation with Claude to process your data

## 🔧 Configuration

### Environment Variables (.env)

```bash
CLAUDE_API_KEY=sk-ant-xxxxx
CONFIDENCE_THRESHOLD=0.7
RATE_LIMIT_DELAY=0.5
LOG_LEVEL=INFO
```

### MCP Tools

**Tool 1: get_acat_reference**
- Loads ACAT reference datastore names
- Called ONCE at start
- Returns: `{reference_list: [...], total_count: 449}`

**Tool 2: endoflife_lookup**
- Queries endoflife.date API for version/EOL info
- Called for low-confidence matches (< 0.7)
- Input: `{product: "PostgreSQL", version: "14"}`
- Output: EOL date, support status, latest version, etc.

## 🧪 Testing

Use test data:
```bash
# Test file included: input/test_user_input.xlsx (21 test cases)
cd python_agent
python agent.py
```

Test cases cover:
- Exact matches
- Typos (PostGres, MaroaDB)
- Case variations
- Version suffixes (.x, -log)
- Low confidence matches

## 🐛 Troubleshooting

**Problem**: `ModuleNotFoundError`
- **Fix**: `pip install -r requirements.txt`

**Problem**: `Failed to connect to MCP server`
- **Fix**: Verify `mcp_server/server.py` exists

**Problem**: `ACAT reference file not found`
- **Fix**: Place file in `mcp_server/data/ACAT_Data_Stores_Master.xlsx`

**Problem**: `Authentication error`
- **Fix**: Check `CLAUDE_API_KEY` in `.env`

**Problem**: Rate limiting (429 errors)
- **Fix**: Increase `RATE_LIMIT_DELAY` in `.env`

## 📊 Output Files

### 1. datastore_match_results.xlsx
All matching results with confidence scores (7 columns).

### 2. api_success.xlsx
Successful EOL lookups (11 columns):
- Input Datastore, Product, Version
- API Matched Version, Match Type
- EOL Date, Support Status
- Latest Version, LTS Version, Release Date

### 3. api_not_found.xlsx
Products not found in endoflife.date (7 columns):
- Input Datastore, Product, Version
- Not Found Type
- Available Versions, Error Message

### 4. api_errors.xlsx
API errors during lookups (8 columns):
- Input Datastore, Product, Version
- Error Type, Error Details
- Retry Count, Timestamp

## 🎓 Key Implementation Details

- **MCP Server**: Data access only, no business logic
- **LLM Matching**: Agent's native capability (not MCP tool)
- **Tool Descriptions**: Serve as workflow documentation
- **Error Handling**: Always returns structured responses
- **Rate Limiting**: 0.5s between API calls
- **Retries**: 3 attempts with exponential backoff

## 📚 Additional Resources

- **MCP Documentation**: https://modelcontextprotocol.io
- **Claude API**: https://docs.anthropic.com
- **endoflife.date API**: https://endoflife.date/docs/api

## 📄 License

Internal ATOS project - All rights reserved.
