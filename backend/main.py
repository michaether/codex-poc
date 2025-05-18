from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import openai
import os
import json
from datetime import datetime
import re
import shutil

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
    # extract hotel name after "hotel name:" and slugify
    match = re.search(r'hotel name:\s*"?([^"\n]+)"?', prompt, re.IGNORECASE)
    hotel_name = match.group(1) if match else 'hotel'
    slug = re.sub(r'[^a-z0-9]+', '_', hotel_name.lower()).strip('_')

    folder_name = f'site_{timestamp}_{slug}'
    folder_path = os.path.join('generated_sites', folder_name)
    os.makedirs(folder_path, exist_ok=True)

    filepath = os.path.join(folder_path, 'index.html')
    with open(filepath, 'w') as f:
        f.write(content)

    # copy required assets into the folder
    image_map = {
        'hero-bg.webp': 'spa-hotel-hero-768x352.webp',
        'casino-bg.webp': 'casino-hotels-6-768x358.webp',
        'hotel1.webp': 'Casino-Hotels-4-150x150.webp',
        'hotel2.webp': 'Casino-Hotels-5-150x150.webp',
        'hotel3.jpg': 'pexels-olly-3786784-300x200.jpg',
        'hotel4.jpg': 'pexels-olly-3786784-768x512.jpg',
        'retreat1.webp': '21-Club-Steak-Seafood-300x104.webp',
        'retreat2.webp': 'Baccarat-300x104.webp',
        'waterside.webp': 'Banff-Caribou-Lodge-300x224.webp',
        'forest.webp': 'Bar-Barista-1-300x125.webp',
        'playstay.webp': 'Blackjack-150x150.webp',
        'casino-royale.webp': 'Casino-Hotels-5.webp',
    }
    for dest, src in image_map.items():
        src_path = os.path.join('assets', src)
        if os.path.exists(src_path):
            shutil.copy(src_path, os.path.join(folder_path, dest))

    # create simple svg icons
    icons = {
        'fb-icon.svg': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="blue"/><text x="10" y="15" font-size="12" fill="white" text-anchor="middle">f</text></svg>',
        'twitter-icon.svg': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="skyblue"/><text x="10" y="15" font-size="12" fill="white" text-anchor="middle">t</text></svg>',
        'youtube-icon.svg': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="red"/><polygon points="8,5 15,10 8,15" fill="white"/></svg>',
    }
    for name, content_str in icons.items():
        with open(os.path.join(folder_path, name), 'w') as f:
            f.write(content_str)

    # create placeholder pages for nav links
    pages = [
        'who_we_are.html',
        'waterside_retreats.html',
        'into_the_forest.html',
        'canada_playstay.html',
        'promotions.html',
        'get_in_touch.html',
    ]
    placeholder = "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>{0}</title></head><body><h1>{0}</h1><p>Placeholder page.</p></body></html>"
    for page in pages:
        title = page.replace('_', ' ').replace('.html', '').title()
        with open(os.path.join(folder_path, page), 'w') as f:
            f.write(placeholder.format(title))

    site_entry = f"{folder_name}/index.html"
    sites_data.append({'prompt': prompt, 'file': site_entry})
    with open(DATA_FILE, 'w') as f:
        json.dump(sites_data, f)
    return templates.TemplateResponse('generated.html', {'request': request, 'file': site_entry})
