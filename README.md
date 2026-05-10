# Financial-Statement-Analysis

Extract structured financial data from 10-K PDF reports using OpenAI-compatible vision models. Automatically detects and analyzes all three core financial statements — balance sheet, income statement, and cash flow statement — then produces a consolidated cross-statement analysis.

Works with any OpenAI-compatible endpoint: Ollama, OpenAI, Together, Groq, LM Studio, vLLM, etc.

## Key Features

- **No third-party APIs needed** — All data is extracted directly from the PDF using vision LLMs. No external financial data services or web scraping required.
- **Automatic page detection** — Simply drop in any 10-K PDF; the tool automatically locates the relevant statement pages. No need to specify exact page numbers.
- **Multi-statement analysis** — Extracts balance sheet, income statement, and cash flow statement in a single run.
- **Cross-statement indicators** — Calculates ROA, ROE, EBITDA, Free Cash Flow, and more by combining data across all three statements.

## What It Does

For each PDF, the tool:

1. Locates the balance sheet, income statement, and cash flow statement pages via keyword scoring
2. Converts each detected page to an image
3. Sends each image to a vision LLM to extract structured financial data (current + prior period)
4. Calculates per-statement financial indicators
5. Produces a consolidated report with cross-statement indicators (ROA, ROE, EBITDA, etc.)

## Setup

```bash
conda create -n fin python=3.12
conda activate fin
pip install -r requirements.txt
```

### Ollama (Local)

1. Install Ollama: https://ollama.com
2. Pull a vision model:
   ```bash
   ollama pull qwen3.5:latest
   ```
3. Verify connectivity:
   ```bash
   python -m tests.test_connection
   ```

## Configuration

Edit `.env` at the project root:

```env
MODEL=qwen3.5:latest
BASE_URL=http://localhost:11434/v1/
API_KEY=EMPTY
```

OpenAI example:
```env
MODEL=gpt-5.5
BASE_URL=https://api.openai.com/v1
API_KEY=sk-...
```

Environment variables (`MODEL`, `BASE_URL`, `API_KEY`) override `.env` values.

## Usage

### Web Dashboard

Start the web server for an interactive UI:

```bash
python main.py
```

Then open http://localhost:8000 in your browser. Upload PDFs and view extracted results in real-time.