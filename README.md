# Hotel Website Builder POC

This proof of concept demonstrates a very simple hotel website generator. A FastAPI backend accepts a text description and uses OpenAI to provide short text snippets which are inserted into a reusable HTML template. Generated websites are stored locally and can be viewed through the interface.

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
3. Open `http://localhost:8085` in your browser.

Generated sites are saved in the `generated_sites/` folder. The full Bootstrap library is bundled in `static/bootstrap/` and can be copied into generated sites if desired. Each site now contains an `assets/` subfolder holding its images and icons. The HTML layout lives in `templates/hotel/hotel_index.html`; OpenAI only supplies the text content inserted into that template.
OpenAI now returns text for many sections such as feature cards and benefits which populate this template.

### Hero Images

When selecting a hero image for a site, choose a file that is at least **300 KB**. Images smaller than this may appear grainy when used full width.

For the **lifestyle** template the hero image is fixed to `hero_1.jpg`. This file is automatically copied into each generated site that uses the lifestyle template.

### Response Caching

OpenAI responses are cached in `generated_sites/openai_cache.json`. The key is the
combination of the user prompt and selected template. If a matching entry is
found in this file, the stored JSON is reused instead of requesting new content
from the API. Any new completions are written back to the cache automatically.

OPENAI_API_KEY=your-key-here uvicorn backend.main:app --reload
