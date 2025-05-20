# AI Money Printer Shorts Generator

A streamlined application for automating the creation of short-form videos, from script to publication.

## Features

- **Video Blueprint Setup:** Configure video duration and B-Roll segments
- **Script Segmentation:** Break down script into A-Roll and B-Roll segments
- **B-Roll Prompt Generation:** Create optimized prompts for AI image/video generation
- **Parallel Content Production:** Generate A-Roll and B-Roll simultaneously
- **Seamless Video Assembly:** Stitch all segments together with perfect timing
- **Captioning Enhancement:** Add stylized auto-captions synced with voice
- **Multi-Platform Publishing:** Export for YouTube, TikTok, and Instagram

## Setup Instructions

1. **Install Dependencies:**
   ```
   cd app
   pip install -r requirements.txt
   ```

2. **Run the Application:**
   ```
   cd app
   streamlit run Home.py
   ```

3. **Access the Application:**
   Open your browser and go to http://localhost:8501

## Project Structure

- `app/`: Main application directory
  - `Home.py`: Main entry point
  - `pages/`: Individual workflow pages
  - `components/`: Reusable UI components
  - `utils/`: Helper functions
  - `services/`: External API integrations
  - `models/`: Data models
  - `config/`: Application settings
  - `assets/`: Static resources

## Technical Requirements

- Python 3.9+
- FFmpeg (for video processing)

## License

This software is provided for personal use only.
