from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import openai
import os
import json
from datetime import datetime

app = FastAPI()

# Mount static files to serve generated sites and local libraries
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/sites', StaticFiles(directory='generated_sites'), name='sites')
app.mount('/assets', StaticFiles(directory='assets'), name='assets')

# Directory to store generation metadata
DATA_FILE = 'generated_sites/sites.json'
os.makedirs('generated_sites', exist_ok=True)

# Load existing metadata if any
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        sites_data = json.load(f)
else:
    sites_data = []

templates = Jinja2Templates(directory='templates')

# Home page: display form and list of generated sites
@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'sites': sites_data})

# POST endpoint to generate site using OpenAI
@app.post('/generate', response_class=HTMLResponse)
async def generate(request: Request, prompt: str = Form(...)):
    """Generate website HTML/CSS/JS using OpenAI based on user prompt."""
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    system_message = (
        "You generate JSON snippets for a rich hotel landing page. "
        "Return only JSON with keys: title, hero_heading, hero_text, "
        "tagline_heading, tagline_text, "
        "feature1_title, feature1_text, feature2_title, feature2_text, "
        "feature3_title, feature3_text, feature4_title, feature4_text, "
        "casino_heading, casino_text, link1_title, link2_title, "
        "extended1_title, extended1_text, extended1_button, "
        "extended2_title, extended2_text, extended2_button, "
        "extended3_title, extended3_text, extended3_button, "
        "extended4_title, extended4_text, extended4_button, "
        "benefits_heading, benefit1_title, benefit1_text, "
        "benefit2_title, benefit2_text, benefit3_title, benefit3_text.")
    user_message = f"User description: {prompt}"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    content = templates.get_template('template_v2.html').render(**data)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = f'site_{timestamp}.html'
    filepath = os.path.join('generated_sites', filename)
    with open(filepath, 'w') as f:
        f.write(content)
    sites_data.append({'prompt': prompt, 'file': filename})
    with open(DATA_FILE, 'w') as f:
        json.dump(sites_data, f)
    return templates.TemplateResponse('generated.html', {'request': request, 'file': filename})
