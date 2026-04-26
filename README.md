# NHentai Downloader

A fast, reliable Python tool to download galleries from nhentai.net with ZIP, CBZ, or PDF output.

## Features

- Fast Downloads - Downloads 10 images simultaneously
- Multiple Formats - ZIP, CBZ, or PDF output
- Batch Download - Download multiple galleries at once (comma separated IDs or URLs)
- GUI and CLI - Both graphical and command-line interfaces available
- Auto-Delete - Option to remove original images after conversion
- Config File - Saves your preferences for next time
- No External Dependencies - Only uses requests library

## Requirements

- Python 3.7 or higher
- Internet connection
- requests library (pip install requests)

Optional for PDF output:
- Pillow
- img2pdf

## Installation

1. Download the script(s) to a folder of your choice
2. Install dependencies:
   pip install requests

For PDF support:
   pip install Pillow img2pdf

## How to Use

GUI Version (Recommended):

   python nhentai_gui.py

CLI Version:

   python nhentai.py

Input Examples:

   Single gallery: 123456
   Multiple galleries: 123456, 789012, 345678
   Using URL: https://nhentai.net/g/123456/

## File Structure

your_script_folder/
├── nhentai_gui.py
├── nhentai.py
├── downloads/                 (your ZIP/CBZ/PDF files)
├── nhentai/                   (original images)
└── nhentai_config.json        (settings)

## Speed

Downloads approximately 10 images per second on a standard connection.

## Common Issues

Problem                          Solution
requests not found               pip install requests
Pillow not installed             pip install Pillow (for PDF)
img2pdf not installed            pip install img2pdf (for PDF)

## License

MIT License

## Disclaimer

For personal use only. Please respect the website's terms of service.
