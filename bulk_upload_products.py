import os
import zipfile
import requests
import shutil
import re
from pathlib import Path
from tqdm import tqdm

BACKEND_URL = "http://127.0.0.1:5001/api/products"
ZIP_PATH = "pictures.zip"
TEMP_UNZIP = "temp_bulk_upload"
OPENAI_API_KEY = ""  # Optional: Add OpenAI key for AI-generated descriptions

def ai_generate_description(title, gender, category):
    if not OPENAI_API_KEY:
        return f"{title}: A trendy {category} for {gender}, perfect for every wardrobe!"
    import openai
    openai.api_key = OPENAI_API_KEY
    prompt = (
        f"Write a cool, modern product description (2-3 lines) for a Pakistani fashion website. "
        f"Product: {title}. Gender: {gender}. Category: {category}. "
        "Highlight the style, vibe, and where you could wear it. Keep it catchy and aesthetic."
    )
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You're a creative fashion copywriter."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=60
        )
        return res["choices"][0]["message"]["content"].strip()
    except Exception:
        return f"{title}: Stylish {category} for {gender}, made for modern taste."

def pretty_title(filename):
    name = os.path.splitext(os.path.basename(filename))[0]
    name = re.sub(r'[_\-]+', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.title()

def main():
    # Clean previous extraction
    if os.path.exists(TEMP_UNZIP):
        shutil.rmtree(TEMP_UNZIP, ignore_errors=True)

    # Unzip files
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(TEMP_UNZIP)

    # Gather images and meta
    uploads = []
    for root, dirs, files in os.walk(TEMP_UNZIP):
        for file in files:
            if file.lower().endswith(('jpg', 'jpeg', 'png', 'gif')):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, TEMP_UNZIP)
                parts = Path(rel_path).parts
                # Expecting at least: gender/category/subcategory/image.jpg
                if len(parts) < 3:
                    print(f"Skipping {rel_path}: needs [Gender]/[Category]/[Subcategory]/img.jpg")
                    continue

                # -- Main Fix: extract correctly --
                gender = parts[0].replace("_", " ").title()    # e.g. "Women Wear"
                category = parts[1].replace("_", " ").title()  # e.g. "Winter"
                # If you want to use subcategory, merge with title
                if len(parts) > 3:
                    subcategory = parts[2].replace("_", " ").title()
                    title = f"{subcategory} {pretty_title(file)}"
                else:
                    title = pretty_title(file)

                description = ai_generate_description(title, gender, category)
                uploads.append((full_path, title, description, gender, category))

    print(f"Found {len(uploads)} products to upload.")

    # Upload to backend
    for img_path, title, description, gender, category in tqdm(uploads):
        files = {'image_file': open(img_path, 'rb')}
        data = {
            'title': title,
            'description': description,
            'gender': gender,
            'category': category,
        }
        try:
            resp = requests.post(BACKEND_URL, files=files, data=data)
            resp.raise_for_status()
            print(f"Uploaded: {title} ({gender} / {category})")
        except Exception as e:
            print(f"Failed for {img_path}: {e} / {getattr(resp, 'text', '')}")

    print("All uploads done!")
    # Clean up extracted folder
    shutil.rmtree(TEMP_UNZIP, ignore_errors=True)

if __name__ == "__main__":
    main()
