from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import openai
import os
import json
from datetime import datetime
import re
import shutil
import io
import zipfile
import random

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}


ICON_KEYWORDS = {
    'phone': 'phone',
    'laptop': 'laptop',
    'camera': 'camera',
    'watch': 'smartwatch',
    'tv': 'tv',
    'television': 'tv',
    'tablet': 'tablet',
    'headphone': 'headphones',
    'speaker': 'speaker',
    'printer': 'printer',
    'car': 'car-front',
    'book': 'book',
    'chair': 'chair',
}


def choose_icon(name: str) -> str:
    """Return a bootstrap icon name based on keywords in *name*."""
    lowered = name.lower()
    for key, icon in ICON_KEYWORDS.items():
        if key in lowered:
            return icon
    return 'box'


def list_images(src: str) -> list[str]:
    """Return names of image files in *src* matching ``IMAGE_EXTS``."""
    return [
        f for f in os.listdir(src)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
        and not f.endswith('Zone.Identifier')
    ]


def copy_images(src: str, dst: str, count: int) -> tuple[list[str], list[str]]:
    """Copy up to ``count`` images from *src* to *dst*.

    Returns the selected filenames and the full list of available files.
    """
    files = list_images(src)
    selected = random.sample(files, min(len(files), count))
    for name in selected:
        shutil.copy(os.path.join(src, name), os.path.join(dst, name))
    return selected, files

app = FastAPI()

# Mount static files to serve generated sites and local libraries
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/sites', StaticFiles(directory='generated_sites'), name='sites')
app.mount('/assets', StaticFiles(directory='assets'), name='assets')

# Directory to store generation metadata
DATA_FILE = 'generated_sites/sites.json'
CACHE_FILE = 'generated_sites/openai_cache.json'
os.makedirs('generated_sites', exist_ok=True)

# Load existing metadata if any
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        sites_data = json.load(f)
else:
    sites_data = []

# Load cached OpenAI responses if any
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'r') as f:
        cache_data = json.load(f)
else:
    cache_data = {}

templates = Jinja2Templates(directory='templates')

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'sites': list(reversed(sites_data))})

@app.post('/generate', response_class=HTMLResponse)
async def generate(request: Request, prompt: str = Form(...), template: str = Form('hotel')):
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
    if template == "comparison":
        system_message = (
            "You generate JSON snippets for a product comparison page. "
            "Return only JSON with keys: title, hero_heading, hero_text, "
            "product1_name, product1_pros, product1_cons, "
            "product1_price, product1_rating, "
            "product2_name, product2_pros, product2_cons, "
            "product2_price, product2_rating, "
            "conclusion_title, conclusion_text. "
            "List items for pros and cons should be provided as a "
            "semicolon-separated string, not as a JSON array."

        )
    user_message = f"User description: {prompt}"
    key = f"{prompt}|{template}"
    # Reuse cached response if available
    if key in cache_data:
        data = cache_data[key]
    else:
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
        cache_data[key] = data
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)

    if template == 'comparison':
        data['product1_icon'] = choose_icon(data.get('product1_name', ''))
        data['product2_icon'] = choose_icon(data.get('product2_name', ''))
    if template == 'hotel':
        template_file = 'hotel/hotel_index.html'
    elif template == 'lifestyle':
        template_file = 'lifestyle/lifestyle_index.html'
    else:
        template_file = 'comparison/comparison_index.html'

    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    if template == 'hotel':
        match = re.search(r'hotel name:\s*"?([^"\n]+)"?', prompt, re.IGNORECASE)
        site_name = match.group(1) if match else 'hotel'
    else:
        match = re.search(r'site name:\s*"?([^"\n]+)"?', prompt, re.IGNORECASE)
        site_name = match.group(1) if match else template
    slug = re.sub(r'[^a-z0-9]+', '_', site_name.lower()).strip('_')

    folder_name = f'site_{timestamp}_{slug}'
    folder_path = os.path.join('generated_sites', folder_name)
    assets_path = os.path.join(folder_path, 'assets')
    os.makedirs(assets_path, exist_ok=True)

    # copy required assets into the folder
    if template == 'hotel':
        asset_dir = os.path.join('assets', 'hotel')
        selected, _ = copy_images(asset_dir, assets_path, 12)
        hero_bg = selected[0]
        feature_imgs = selected[1:5]
        retreat_imgs = selected[5:7]
        extended_imgs = selected[7:11]
        casino_bg = selected[11] if len(selected) > 11 else selected[0]

        data.update({
            'hero_bg': hero_bg,
            'casino_bg': casino_bg,
            'feature_imgs': feature_imgs,
            'retreat_imgs': retreat_imgs,
            'extended_imgs': extended_imgs,
        })
    elif template == 'lifestyle':
        asset_dir = os.path.join('assets', 'lifestyle')
        selected, files = copy_images(asset_dir, assets_path, 17)
        # ensure hero_1.jpg is always available since the template references it
        hero_image = 'hero_1.jpg'
        if hero_image not in selected and hero_image in files:
            shutil.copy(os.path.join(asset_dir, hero_image), os.path.join(assets_path, hero_image))
            selected.append(hero_image)
        data['images'] = selected
    else:
        # no asset handling needed for comparison template
        pass

    content = templates.get_template(template_file).render(**data)

    filepath = os.path.join(folder_path, 'index.html')
    with open(filepath, 'w') as f:
        f.write(content)

    # create simple svg icons
    icons = {
        'fb-icon.svg': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="blue"/><text x="10" y="15" font-size="12" fill="white" text-anchor="middle">f</text></svg>',
        'twitter-icon.svg': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="skyblue"/><text x="10" y="15" font-size="12" fill="white" text-anchor="middle">t</text></svg>',
        'youtube-icon.svg': '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="red"/><polygon points="8,5 15,10 8,15" fill="white"/></svg>',
    }
    for name, content_str in icons.items():
        with open(os.path.join(assets_path, name), 'w') as f:
            f.write(content_str)

    if template == 'hotel':
        # create placeholder pages for nav links
        pages = [
            'who_we_are.html',
            'waterside_retreats.html',
            'into_the_forest.html',
            'canada_playstay.html',
            'promotions.html',
            'get_in_touch.html',
        ]
        placeholder = (
            "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>{0}</title></head>"
            "<body><h1>{0}</h1><p>Placeholder page.</p></body></html>"
        )
        for page in pages:
            title = page.replace('_', ' ').replace('.html', '').title()
            with open(os.path.join(folder_path, page), 'w') as f:
                f.write(placeholder.format(title))
    elif template == 'lifestyle':
        # copy static lifestyle section pages
        lifestyle_pages = ['health.html', 'pets.html', 'tech.html']
        for page in lifestyle_pages:
            src = os.path.join('templates', 'lifestyle', page)
            dst = os.path.join(folder_path, page)
            shutil.copy(src, dst)
    else:
        # no additional pages for comparison template
        pass

    site_entry = f"{folder_name}/index.html"
    sites_data.append({'prompt': prompt, 'file': site_entry})
    with open(DATA_FILE, 'w') as f:
        json.dump(sites_data, f)
    return templates.TemplateResponse(
        'generated.html',
        {'request': request, 'file': site_entry, 'folder': folder_name}
    )


@app.get('/download/{folder}')
async def download_site(folder: str):
    """Download a generated site as a zip archive."""
    folder_path = os.path.join('generated_sites', folder)
    if not os.path.isdir(folder_path):
        return HTMLResponse('Site not found', status_code=404)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root_dir, _, files in os.walk(folder_path):
            for name in files:
                file_path = os.path.join(root_dir, name)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
    buffer.seek(0)

    headers = {'Content-Disposition': f'attachment; filename={folder}.zip'}
    return StreamingResponse(buffer, media_type='application/zip', headers=headers)


@app.get('/preview/{template}', response_class=HTMLResponse)
async def preview_template(template: str):
    if template not in {'hotel', 'lifestyle', 'comparison'}:
        return HTMLResponse('Template not found', status_code=404)

    if template == 'comparison':
        demo = {
            'title': 'Demo Site',
            'hero_heading': 'Welcome!',
            'hero_text': 'Sample hero text.',
            'product1_name': 'Product 1',
            'product1_icon': choose_icon('Product 1'),
            'product1_price': '$49',
            'product1_rating': '4.5/5',
            'product1_pros': 'Fast; Reliable',
            'product1_cons': 'Expensive; Limited colors',
            'product2_name': 'Product 2',
            'product2_icon': choose_icon('Product 2'),
            'product2_price': '$59',
            'product2_rating': '4/5',
            'product2_pros': 'Affordable; Stylish',
            'product2_cons': 'Slow updates; Fewer accessories',
            'conclusion_title': 'Conclusion',
            'conclusion_text': 'Summary text.',
        }
        html = templates.get_template('comparison/comparison_index.html').render(**demo)
        return HTMLResponse(html)

    demo = {
        'title': 'Demo Site',
        'hero_heading': 'Welcome!',
        'hero_text': 'Sample hero text.',
        'tagline_heading': 'Tagline',
        'tagline_text': 'Short description.',
        'feature1_title': 'Feature 1',
        'feature1_text': 'Feature 1 text',
        'feature2_title': 'Feature 2',
        'feature2_text': 'Feature 2 text',
        'feature3_title': 'Feature 3',
        'feature3_text': 'Feature 3 text',
        'feature4_title': 'Feature 4',
        'feature4_text': 'Feature 4 text',
        'casino_heading': 'Casino Fun',
        'casino_text': 'Casino description',
        'link1_title': 'Link 1',
        'link2_title': 'Link 2',
        'extended1_title': 'Ext 1',
        'extended1_text': 'Ext 1 text',
        'extended1_button': 'Read',
        'extended2_title': 'Ext 2',
        'extended2_text': 'Ext 2 text',
        'extended2_button': 'Read',
        'extended3_title': 'Ext 3',
        'extended3_text': 'Ext 3 text',
        'extended3_button': 'Read',
        'extended4_title': 'Ext 4',
        'extended4_text': 'Ext 4 text',
        'extended4_button': 'Read',
        'benefits_heading': 'Benefits',
        'benefit1_title': 'Benefit 1',
        'benefit1_text': 'Benefit 1 text',
        'benefit2_title': 'Benefit 2',
        'benefit2_text': 'Benefit 2 text',
        'benefit3_title': 'Benefit 3',
        'benefit3_text': 'Benefit 3 text',
    }
    template_file = (
        'hotel/hotel_index.html'
        if template == 'hotel'
        else 'lifestyle/lifestyle_index.html'
    )

    if template == 'hotel':
        asset_dir = os.path.join('assets', 'hotel')
        files = list_images(asset_dir)
        selected = random.sample(files, min(len(files), 12))
        demo.update({
            'hero_bg': '/assets/hotel/' + selected[0],
            'feature_imgs': ['/assets/hotel/' + f for f in selected[1:5]],
            'retreat_imgs': ['/assets/hotel/' + f for f in selected[5:7]],
            'extended_imgs': ['/assets/hotel/' + f for f in selected[7:11]],
            'casino_bg': '/assets/hotel/' + (selected[11] if len(selected) > 11 else selected[0]),
        })
    else:
        asset_dir = os.path.join('assets', 'lifestyle')
        files = list_images(asset_dir)
        selected = random.sample(files, min(len(files), 17))
        demo['images'] = ['/assets/lifestyle/' + f for f in selected]

    html = templates.get_template(template_file).render(**demo)
    return HTMLResponse(html)
