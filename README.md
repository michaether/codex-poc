# Hotel Website Builder POC

This proof of concept demonstrates a very simple hotel website generator. A FastAPI backend accepts a text description and uses OpenAI to create a single page application. Generated websites are stored locally and can be viewed through the interface.

## Requirements

- Python 3.10+
- openai>=1.0.0
- An OpenAI API key (set `OPENAI_API_KEY` environment variable)

## Setup

1. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Run the development server:
   ```bash
   uvicorn backend.main:app --reload
   ```
3. Open `http://localhost:8000` in your browser.

Generated sites are saved in the `generated_sites/` folder. A minimal Bootstrap CSS file is included in `static/` for offline use.
