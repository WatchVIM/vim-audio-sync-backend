# VIM AudioSync Backend – Notes

## Repo Layout

```text
vim-audio-sync-backend/
├── app.py                 # Flask backend (upload, preview, download, PayPal hooks)
├── requirements.txt       # Python dependencies
├── README.md              # Main project overview and setup instructions
├── uploads/               # Runtime raw uploads (ignored in git)
├── outputs/               # Runtime synced outputs (ignored in git)
├── checkout.html          # Subscription checkout page (PayPal)
├── uploads.html           # Front-end upload UI
├── outputs.html           # Job status / output viewer
├── templates/
│   └── preview.html       # Jinja template for preview player
└── misc/
    └── notes.md           # This file
