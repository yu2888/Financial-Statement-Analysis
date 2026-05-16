# Financial-Statement-Analysis
![Banner](/asset/image1.png)

Extract structured financial data from 10-K PDF reports using vision LLM. Automatically detects and analyzes all three core financial statements — balance sheet, income statement, and cash flow statement — then produces a consolidated cross-statement analysis.

Works with any OpenAI-compatible endpoint: Ollama, OpenAI, OpenRouter, Groq, LM Studio, vLLM, etc.

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
conda create -n <your-env-name> python=3.12
conda activate <your-env-name>
pip install -r requirements.txt
```

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your settings. Examples:

**OpenAI:**
```env
MODEL=gpt-5.5
BASE_URL=https://api.openai.com/v1
API_KEY=sk-your-openai-api-key
```

**Ollama (Local):**
```env
MODEL=qwen3.5:latest
BASE_URL=http://localhost:11434/v1/
API_KEY=EMPTY
```

Environment variables (`MODEL`, `BASE_URL`, `API_KEY`) override `.env` values.

## Demo
![Analysis Results](/asset/image2.png)
![Report Output](/asset/image3.png)

## Usage

### Web Dashboard (for humans)

Interactive UI for uploading PDFs and viewing results in real-time:

```bash
python main.py
```

Open http://localhost:8000 in your browser.

### CLI (for agents/automation)

Process PDFs programmatically:

```bash
# Process all PDFs in data/
python main.py --cli

# Process specific PDF
python main.py data/amz-10k.pdf
```