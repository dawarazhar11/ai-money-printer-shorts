# ReelForge

An end-to-end automation platform for creating short-form videos. Takes you from script to published content across YouTube, TikTok, and Instagram with AI-powered generation at every step.

## Features

- **Script Segmentation** -- Break scripts into A-Roll (narration) and B-Roll (visuals) with LLM assistance via Ollama
- **AI Visual Generation** -- Generate B-Roll images/videos through ComfyUI (Flux, WAN, LoRA workflows) or Replicate
- **Avatar Video** -- Create talking-head A-Roll segments using HeyGen avatars
- **Video Assembly** -- Stitch A-Roll and B-Roll with audio sync and transitions
- **Styled Captions** -- Word-by-word animated captions with multiple effects (fade, scale, highlight)
- **Multi-Platform Publishing** -- Export and upload to YouTube, TikTok, and Instagram

## Prerequisites

- Python 3.9+
- FFmpeg installed and available on PATH
- At least one of:
  - [ComfyUI](https://github.com/comfyanonymous/ComfyUI) server (for image/video generation)
  - [Replicate](https://replicate.com/) API token
- [Ollama](https://ollama.ai/) (for local LLM-based prompt generation)
- [HeyGen](https://www.heygen.com/) API key (for avatar videos)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/dawarazhar11/ai-money-printer-shorts.git
cd ai-money-printer-shorts

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and server URLs

# Run the application
cd app
streamlit run Home.py
```

Then open http://localhost:8501 in your browser.

## Configuration

Copy `.env.example` to `.env` and set your values:

| Variable | Description |
|---|---|
| `COMFYUI_IMAGE_API_URL` | ComfyUI server for image generation |
| `COMFYUI_VIDEO_API_URL` | ComfyUI server for video generation |
| `OLLAMA_API_URL` | Ollama API endpoint |
| `HEYGEN_API_KEY` | HeyGen API key for avatar videos |
| `REPLICATE_API_TOKEN` | Replicate API token |

## Workflow

The application guides you through an 8-step pipeline:

1. **Settings** -- Configure project name, duration, and API connections
2. **Blueprint** -- Visualize the video structure and segment layout
3. **Script Segmentation** -- Organize your script into A-Roll and B-Roll sections
4. **B-Roll Prompts** -- Generate optimized prompts for AI visual generation
5. **Content Production** -- Generate A-Roll (HeyGen) and B-Roll (ComfyUI/Replicate) in parallel
6. **Video Assembly** -- Stitch segments together with audio synchronization
7. **Captioning** -- Add styled, word-synced captions with animation effects
8. **Publishing** -- Export and upload to social media platforms

## Project Structure

```
.
├── app/
│   ├── Home.py                  # Streamlit entry point
│   ├── pages/                   # Workflow step pages (1-8)
│   ├── components/              # Reusable UI components
│   ├── utils/                   # Helpers (HeyGen API, video processing, audio)
│   ├── config/                  # App config & user data
│   ├── workflows/               # ComfyUI workflow templates (JSON)
│   ├── fonts/                   # Font files for captions
│   ├── assets/                  # CSS and static resources
│   ├── scripts/                 # Maintenance & utility scripts
│   ├── tests/                   # Test suite
│   └── media/                   # Generated media output
├── docs/                        # Documentation
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
└── README.md
```

## License

This software is provided for personal use only.
