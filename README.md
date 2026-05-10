# Financial-Statement-Analysis
<img width="1331" height="749" alt="image1" src="https://github.com/user-attachments/assets/6ed49902-bc20-4b87-84c4-dd452e07904b" />

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

## Demo
<img width="2535" height="1316" alt="image2" src="https://github.com/user-attachments/assets/74fd82ed-2bf0-4e65-b4b0-80f8e2f7b838" />
<img width="2525" height="1328" alt="image3" src="https://github.com/user-attachments/assets/c1ec0e30-d3f0-4f5d-9a9b-57f6cc305c48" />
