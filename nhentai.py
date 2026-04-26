# save as nhentai_ultimate.py
import os
import zipfile
import shutil
import re
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Check for img2pdf
try:
    import img2pdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

print("=" * 60)
print("NHENTAI DOWNLOADER (API)")
print("=" * 60)

if not PDF_AVAILABLE:
    print("\n⚠️ img2pdf not installed. PDF output disabled.")
    print("   Install with: pip install img2pdf")

# ========== SETUP DIRECTORIES ==========
script_dir = Path(__file__).parent.absolute()
output_dir = script_dir / "downloads"
output_dir.mkdir(parents=True, exist_ok=True)

images_dir = script_dir / "nhentai"
images_dir.mkdir(parents=True, exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ========== GET GALLERY IDS ==========
gallery_input = input("\nEnter Gallery ID(s): ").strip()
print("-" * 40)

if ',' in gallery_input:
    batch_ids = [id.strip() for id in gallery_input.split(',') if id.strip()]
    print(f"Multiple mode: {len(batch_ids)} galleries")
else:
    if 'nhentai.net' in gallery_input:
        match = re.search(r'/g/(\d+)/?', gallery_input)
        if match:
            gallery_id = match.group(1)
        else:
            print("Error: Could not extract ID from URL")
            exit()
    else:
        gallery_id = gallery_input
    batch_ids = [gallery_id]
    print("Single mode: 1 gallery")

if len(batch_ids) <= 10:
    for gid in batch_ids:
        print(f"  - {gid}")
print("-" * 40)

# ========== SETTINGS ==========
print("\nSettings (applies to all galleries)")
print("-" * 40)

print("\nOutput format:")
print("  1. ZIP")
print("  2. CBZ")
if PDF_AVAILABLE:
    print("  3. PDF")
format_choice = input("\nChoose (1/2/3): ").strip()

if format_choice == '2':
    output_format = "cbz"
elif format_choice == '3' and PDF_AVAILABLE:
    output_format = "pdf"
else:
    output_format = "zip"
print(f"Format: {output_format.upper()}")

delete_choice = input("\nDelete original images after conversion? (y/n): ").strip().lower()
auto_delete = (delete_choice == 'y')
print(f"Auto-delete: {'ON' if auto_delete else 'OFF'}")

# ========== FUNCTION TO FETCH GALLERY ==========
def fetch_gallery(gallery_id):
    try:
        api_url = f"https://nhentai.net/api/v2/galleries/{gallery_id}"
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            print(f"  API returned {response.status_code}")
            return None
        
        data = response.json()
        gallery = data.get('gallery', data)
        
        return {
            'id': gallery_id,
            'media_id': gallery.get('media_id'),
            'num_pages': gallery.get('num_pages'),
            'title': gallery.get('title', {}).get('pretty', f"gallery_{gallery_id}"),
            'pages': gallery.get('pages', [])
        }
    except Exception as e:
        print(f"  Error: {e}")
        return None

# ========== FUNCTION TO DOWNLOAD PAGE ==========
def download_page(page_num, img_path, gallery_folder):
    url = f"https://i.nhentai.net/{img_path}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            ext = img_path.split('.')[-1]
            filename = f"{page_num:03d}.{ext}"
            filepath = gallery_folder / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return True
    except:
        pass
    return False

# ========== DOWNLOAD PHASE ==========
print("\n" + "=" * 60)
print("PHASE 1: DOWNLOADING GALLERIES")
print("=" * 60)

total_success = 0
total_failed = []
downloaded_galleries = []

for gallery_id in batch_ids:
    print(f"\n[{total_success + 1}/{len(batch_ids)}] ID: {gallery_id}")
    
    gallery = fetch_gallery(gallery_id)
    if not gallery:
        print(f"  Failed to fetch gallery info")
        total_failed.append(gallery_id)
        continue
    
    print(f"  Title: {gallery['title'][:50]}...")
    print(f"  Pages: {gallery['num_pages']}")
    
    safe_title = re.sub(r'[^\w\s-]', '', gallery['title']).strip()
    safe_title = re.sub(r'[-\s]+', '_', safe_title)
    folder_name = f"{gallery_id}_{safe_title}"
    
    gallery_folder = images_dir / folder_name
    gallery_folder.mkdir(parents=True, exist_ok=True)
    
    print(f"  Downloading {gallery['num_pages']} images...")
    
    downloaded = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        for page in gallery['pages']:
            futures[executor.submit(download_page, page['number'], page['path'], gallery_folder)] = page['number']
        
        for future in as_completed(futures):
            if future.result():
                downloaded += 1
            print(f"    Progress: {downloaded}/{gallery['num_pages']}", end='\r')
    
    print(f"\n    Downloaded: {downloaded}/{gallery['num_pages']}")
    
    if downloaded == 0:
        shutil.rmtree(gallery_folder)
        total_failed.append(gallery_id)
        continue
    
    downloaded_galleries.append({
        'folder_name': folder_name,
        'gallery_folder': gallery_folder,
        'title': gallery['title'],
        'num_pages': downloaded
    })
    total_success += 1

if total_success == 0:
    print("\nNo galleries downloaded. Exiting.")
    exit()

# ========== PROCESSING PHASE ==========
print("\n" + "=" * 60)
print(f"PHASE 2: CONVERTING TO {output_format.upper()}")
print("=" * 60)

total_size_mb = 0
processed_folders = []

# Import PIL only if needed
if output_format != 'pdf':
    try:
        from PIL import Image
        PILLOW_AVAILABLE = True
    except ImportError:
        PILLOW_AVAILABLE = False
        print("\n⚠️ Pillow not installed. Using original images.")
else:
    from PIL import Image
    PILLOW_AVAILABLE = True

for i, gallery in enumerate(downloaded_galleries, 1):
    print(f"\n[{i}/{total_success}] {gallery['folder_name']}")
    
    images = sorted(gallery['gallery_folder'].glob("*.jpg")) + sorted(gallery['gallery_folder'].glob("*.png")) + sorted(gallery['gallery_folder'].glob("*.webp"))
    images.sort()
    
    if not images:
        print("  No images found")
        continue
    
    print(f"  Images: {len(images)}")
    
    folder_original_size = sum(img.stat().st_size for img in images) / (1024 * 1024)
    print(f"  Original size: {folder_original_size:.2f} MB")
    
    output_file = output_dir / f"{gallery['folder_name']}.{output_format}"
    
    if output_format == 'pdf':
        print(f"  Creating PDF...")
        
        temp_pdf_folder = script_dir / "temp_pdf"
        temp_pdf_folder.mkdir(parents=True, exist_ok=True)
        
        pdf_images = []
        for idx, img_path in enumerate(images, 1):
            temp_img = temp_pdf_folder / f"{idx:03d}.jpg"
            try:
                with Image.open(img_path) as im:
                    if im.mode in ('RGBA', 'LA', 'P'):
                        rgb_im = Image.new('RGB', im.size, (255, 255, 255))
                        if im.mode == 'RGBA':
                            rgb_im.paste(im, mask=im.split()[-1])
                        else:
                            rgb_im.paste(im)
                        im = rgb_im
                    elif im.mode != 'RGB':
                        im = im.convert('RGB')
                    im.save(temp_img, 'JPEG', quality=95)
                    pdf_images.append(str(temp_img))
            except:
                shutil.copy2(img_path, temp_img)
                pdf_images.append(str(temp_img))
            
            if idx % 20 == 0 or idx == len(images):
                print(f"    Preparing: {idx}/{len(images)}", end='\r')
        
        print(f"\n    Creating PDF file...")
        
        with open(output_file, "wb") as f:
            f.write(img2pdf.convert(pdf_images))
        
        shutil.rmtree(temp_pdf_folder)
        
        final_size = output_file.stat().st_size / (1024 * 1024)
        total_size_mb += final_size
        print(f"  Created: {output_file.name}")
        print(f"  Size: {final_size:.2f} MB")
        
    else:
        # ZIP or CBZ
        print(f"  Creating {output_format.upper()}...")
        
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for idx, img_path in enumerate(images, 1):
                if idx % 10 == 0 or idx == len(images):
                    print(f"    Archiving: {idx}/{len(images)}", end='\r')
                arcname = img_path.relative_to(images_dir)
                zipf.write(img_path, arcname)
        
        print(f"\n  Created: {output_file.name}")
        final_size = output_file.stat().st_size / (1024 * 1024)
        total_size_mb += final_size
        print(f"  Size: {final_size:.2f} MB")
    
    processed_folders.append(gallery['gallery_folder'])

# ========== CLEANUP ==========
print("\n[PHASE 3] CLEANUP")
print("=" * 60)

if processed_folders and auto_delete:
    print(f"Deleting {len(processed_folders)} original image folders...")
    for folder in processed_folders:
        try:
            shutil.rmtree(folder)
            print(f"  Deleted: {folder.name}")
        except:
            print(f"  Failed: {folder.name}")
    print("Cleanup complete")
    
    # Clean up temp folder if exists
    temp_pdf_folder = script_dir / "temp_pdf"
    if temp_pdf_folder.exists():
        shutil.rmtree(temp_pdf_folder)
elif not auto_delete:
    print(f"Original images kept (auto-delete was OFF)")

# ========== SUMMARY ==========
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Successful: {total_success}/{len(batch_ids)}")
print(f"Format: {output_format.upper()}")
print(f"Auto-delete: {'ON' if auto_delete else 'OFF'}")
print(f"Total size: {total_size_mb:.2f} MB")
print(f"Location: {output_dir}")

if total_failed:
    print(f"Failed: {', '.join(total_failed)}")

print("\nDone.")