# save as nhentai_gui.py
import os
import zipfile
import shutil
import re
import json
import requests
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# Check for PDF support
try:
    import img2pdf
    from PIL import Image
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class NHentaiDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NHentai Downloader")
        self.root.geometry("700x620")
        self.root.resizable(True, True)
        
        # Variables
        self.gallery_ids = tk.StringVar()
        self.output_format = tk.StringVar(value="zip")
        self.auto_delete = tk.BooleanVar(value=False)
        self.downloading = False
        
        # Setup directories
        self.script_dir = Path(__file__).parent.absolute()
        self.output_dir = self.script_dir / "downloads"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.script_dir / "nhentai"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Load config
        self.config_file = self.script_dir / "nhentai_config.json"
        self.load_config()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="NHentai Downloader", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Gallery IDs input
        ttk.Label(main_frame, text="Gallery ID(s) or URL(s):", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, text="Examples: 123456  or  123456, 789012  or  https://nhentai.net/g/123456/", font=("Arial", 8)).grid(row=2, column=0, sticky=tk.W)
        
        self.id_entry = ttk.Entry(main_frame, textvariable=self.gallery_ids, width=50)
        self.id_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Output Format
        ttk.Label(main_frame, text="Output Format:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=5)
        
        format_frame = ttk.Frame(main_frame)
        format_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(format_frame, text="ZIP", variable=self.output_format, value="zip").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="CBZ", variable=self.output_format, value="cbz").pack(side=tk.LEFT, padx=5)
        
        if PDF_AVAILABLE:
            ttk.Radiobutton(format_frame, text="PDF", variable=self.output_format, value="pdf").pack(side=tk.LEFT, padx=5)
        else:
            ttk.Label(format_frame, text="(PDF not available - install img2pdf & Pillow)", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
        
        # Delete preference
        ttk.Checkbutton(main_frame, text="Delete original images after conversion", variable=self.auto_delete).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Progress bar
        ttk.Label(main_frame, text="Progress:", font=("Arial", 10)).grid(row=7, column=0, sticky=tk.W, pady=5)
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Status log
        ttk.Label(main_frame, text="Status Log:", font=("Arial", 10)).grid(row=9, column=0, sticky=tk.W, pady=5)
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80)
        self.log_text.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=11, column=0, columnspan=2, pady=10)
        
        self.download_btn = ttk.Button(button_frame, text="Download", command=self.start_download)
        self.download_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Open Downloads Folder", command=self.open_downloads).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Settings", command=self.save_config).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(10, weight=1)
        
    def log(self, message, newline=True):
        if not newline:
            current_text = self.log_text.get(1.0, tk.END)
            lines = current_text.split('\n')
            if lines and len(lines) > 1:
                lines[-2] = message
                new_text = '\n'.join(lines[:-1]) + '\n'
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(tk.END, new_text)
            else:
                self.log_text.insert(tk.END, message + "\n")
        else:
            self.log_text.insert(tk.END, message + "\n")
        
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        
    def open_downloads(self):
        os.startfile(self.output_dir)
        
    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.output_format.set(config.get('default_format', 'zip'))
                self.auto_delete.set(config.get('auto_delete', False))
                self.log("Loaded settings from config")
            except:
                pass
                
    def save_config(self):
        config = {
            'default_format': self.output_format.get(),
            'auto_delete': self.auto_delete.get(),
            'output_dir': str(self.output_dir),
            'images_dir': str(self.images_dir)
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
        self.log("Settings saved to config")
        messagebox.showinfo("Success", "Settings saved!")
        
    def fetch_gallery(self, gallery_id):
        try:
            api_url = f"https://nhentai.net/api/v2/galleries/{gallery_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(api_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                self.log(f"  API returned {response.status_code}")
                return None
            
            data = response.json()
            gallery = data.get('gallery', data)
            
            return {
                'id': gallery_id,
                'media_id': gallery.get('media_id'),
                'num_pages': gallery.get('num_pages'),
                'title': gallery.get('title', {}).get('pretty', f"gallery_{gallery_id}"),
                'pages': gallery.get('pages', []),
                'url': f"https://nhentai.net/g/{gallery_id}/"
            }
        except Exception as e:
            self.log(f"  Error: {e}")
            return None
            
    def download_page(self, page_num, img_path, gallery_folder):
        url = f"https://i.nhentai.net/{img_path}"
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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
        
    def start_download(self):
        if self.downloading:
            messagebox.showwarning("Warning", "Download already in progress!")
            return
            
        gallery_input = self.gallery_ids.get().strip()
        if not gallery_input:
            messagebox.showwarning("Warning", "Please enter Gallery ID(s) or URL(s)")
            return
            
        # Parse IDs
        if ',' in gallery_input:
            items = [item.strip() for item in gallery_input.split(',') if item.strip()]
            batch_ids = []
            for item in items:
                if 'nhentai.net' in item:
                    match = re.search(r'/g/(\d+)/?', item)
                    if match:
                        batch_ids.append(match.group(1))
                    else:
                        self.log(f"Warning: Could not extract ID from URL: {item}")
                else:
                    batch_ids.append(item)
        else:
            if 'nhentai.net' in gallery_input:
                match = re.search(r'/g/(\d+)/?', gallery_input)
                if match:
                    batch_ids = [match.group(1)]
                else:
                    messagebox.showerror("Error", "Could not extract ID from URL")
                    return
            else:
                batch_ids = [gallery_input]
                
        if not batch_ids:
            messagebox.showerror("Error", "No valid gallery IDs found")
            return
            
        self.log(f"Starting download for {len(batch_ids)} gallery(s)")
        self.log(f"Format: {self.output_format.get().upper()}")
        
        thread = threading.Thread(target=self.download_worker, args=(batch_ids,))
        thread.daemon = True
        thread.start()
        
    def download_worker(self, batch_ids):
        self.downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        
        total_success = 0
        total_failed = []
        downloaded_galleries = []
        
        # Download Phase
        self.log("\n" + "=" * 50)
        self.log("PHASE 1: DOWNLOADING GALLERIES")
        self.log("=" * 50)
        
        for idx, gallery_id in enumerate(batch_ids):
            self.log(f"\n[{idx+1}/{len(batch_ids)}] ID: {gallery_id}")
            
            gallery = self.fetch_gallery(gallery_id)
            if not gallery:
                self.log(f"  Failed to fetch gallery info")
                total_failed.append(gallery_id)
                continue
            
            # Show the nhentai.net URL
            self.log(f"  URL: {gallery['url']}")
            self.log(f"  Title: {gallery['title'][:50]}...")
            self.log(f"  Pages: {gallery['num_pages']}")
            
            safe_title = re.sub(r'[^\w\s-]', '', gallery['title']).strip()
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            folder_name = f"{gallery_id}_{safe_title}"
            gallery_folder = self.images_dir / folder_name
            gallery_folder.mkdir(parents=True, exist_ok=True)
            
            self.log(f"  Downloading {gallery['num_pages']} images...")
            
            downloaded = 0
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {}
                for page in gallery['pages']:
                    futures[executor.submit(self.download_page, page['number'], page['path'], gallery_folder)] = page['number']
                
                for future in as_completed(futures):
                    if future.result():
                        downloaded += 1
                    self.log(f"    Progress: {downloaded}/{gallery['num_pages']}", newline=False)
            
            self.log(f"\n    Downloaded: {downloaded}/{gallery['num_pages']}")
            
            if downloaded == 0:
                shutil.rmtree(gallery_folder)
                total_failed.append(gallery_id)
                continue
                
            downloaded_galleries.append({
                'folder_name': folder_name,
                'gallery_folder': gallery_folder,
                'title': gallery['title'],
                'num_pages': downloaded,
                'url': gallery['url']
            })
            total_success += 1
            self.progress_bar['value'] = (idx + 1) / len(batch_ids) * 50
            
        if total_success == 0:
            self.log("\nNo galleries downloaded. Exiting.")
            self.downloading = False
            self.download_btn.config(state=tk.NORMAL)
            return
            
        # Processing Phase
        self.log("\n" + "=" * 50)
        self.log(f"PHASE 2: CONVERTING TO {self.output_format.get().upper()}")
        self.log("=" * 50)
        
        output_format = self.output_format.get()
        total_size_mb = 0
        
        for i, gallery in enumerate(downloaded_galleries, 1):
            self.log(f"\n[{i}/{total_success}] {gallery['folder_name']}")
            self.log(f"  URL: {gallery['url']}")
            
            images = sorted(gallery['gallery_folder'].glob("*.jpg")) + sorted(gallery['gallery_folder'].glob("*.png")) + sorted(gallery['gallery_folder'].glob("*.webp"))
            images.sort()
            
            if not images:
                self.log("  No images found")
                continue
                
            self.log(f"  Images: {len(images)}")
            
            folder_size = sum(img.stat().st_size for img in images) / (1024 * 1024)
            self.log(f"  Size: {folder_size:.2f} MB")
            
            output_file = self.output_dir / f"{gallery['folder_name']}.{output_format}"
            
            if output_format == 'pdf' and PDF_AVAILABLE:
                self.log(f"  Creating PDF...")
                
                try:
                    from PIL import Image
                    temp_pdf_folder = self.script_dir / "temp_pdf"
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
                            self.log(f"    Preparing: {idx}/{len(images)}", newline=False)
                    
                    self.log(f"\n    Creating PDF file...")
                    
                    with open(output_file, "wb") as f:
                        f.write(img2pdf.convert(pdf_images))
                    
                    shutil.rmtree(temp_pdf_folder)
                    
                except Exception as e:
                    self.log(f"  PDF creation failed: {e}")
                    continue
                    
            else:
                # ZIP or CBZ
                self.log(f"  Creating {output_format.upper()}...")
                
                with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for idx, img_path in enumerate(images, 1):
                        if idx % 10 == 0 or idx == len(images):
                            self.log(f"    Archiving: {idx}/{len(images)}", newline=False)
                        arcname = img_path.relative_to(self.images_dir)
                        zipf.write(img_path, arcname)
                
                self.log(f"\n  Created: {output_file.name}")
            
            final_size = output_file.stat().st_size / (1024 * 1024)
            total_size_mb += final_size
            self.log(f"  Size: {final_size:.2f} MB")
            
            self.progress_bar['value'] = 50 + ((i + 1) / total_success * 50)
            
        # Cleanup
        self.log("\n" + "=" * 50)
        self.log("PHASE 3: CLEANUP")
        self.log("=" * 50)
        
        if self.auto_delete.get():
            self.log("Deleting temporary folders...")
            for gallery in downloaded_galleries:
                try:
                    if gallery['gallery_folder'].exists():
                        shutil.rmtree(gallery['gallery_folder'])
                        self.log(f"  Deleted: {gallery['gallery_folder'].name}")
                except:
                    pass
            
            temp_pdf_folder = self.script_dir / "temp_pdf"
            if temp_pdf_folder.exists():
                shutil.rmtree(temp_pdf_folder)
                self.log("  Deleted: temp_pdf")
            
            self.log("Cleanup complete")
        else:
            self.log("Original images kept (auto-delete was OFF)")
        
        # Summary
        self.log("\n" + "=" * 50)
        self.log("SUMMARY")
        self.log("=" * 50)
        self.log(f"Successful: {total_success}/{len(batch_ids)}")
        self.log(f"Format: {output_format.upper()}")
        self.log(f"Total size: {total_size_mb:.2f} MB")
        self.log(f"Location: {self.output_dir}")
        
        if total_failed:
            self.log(f"Failed: {', '.join(total_failed)}")
        
        self.log("\nDone!")
        self.progress_bar['value'] = 100
        self.downloading = False
        self.download_btn.config(state=tk.NORMAL)
        messagebox.showinfo("Complete", f"Downloaded {total_success}/{len(batch_ids)} galleries successfully!")


if __name__ == "__main__":
    root = tk.Tk()
    app = NHentaiDownloaderGUI(root)
    root.mainloop()