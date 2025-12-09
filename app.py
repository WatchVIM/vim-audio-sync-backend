#!/usr/bin/env python3
"""
VIM Media | Audio Sync Service (AudioSync v1)

Features:
- Upload multiple camera clips + external audio
- Support standard formats + RAW (.braw, .r3d, .crm) -> ProRes 422 HQ proxy
- Waveform-based sync (camera scratch vs external audio)
- Multi-track .mov output for Adobe Premiere Pro & Final Cut Pro
- Pay-per-job checkout (no account required)
- Subscription options (Indie / Studio / Pro) via PayPal
- Optional user accounts with profile page and sync history
  (kept separate from WatchVIM / Supabase)

Provided as a service by VIM Media, LLC.
"""

import os
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from datetime import datetime

from flask import (
    Flask,
    request,
    send_file,
    Response,
    redirect,
    url_for,
    session,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

import numpy as np
import soundfile as sf
from scipy.signal import correlate


# ============================================================
# CONFIG
# ============================================================

VIDEO_EXTS = {
    ".mp4", ".mov", ".mxf", ".avi", ".mkv",
    ".braw",  # Blackmagic RAW
    ".r3d",   # RED RAW
    ".crm",   # Canon Cinema RAW
}

RAW_VIDEO_EXTS = {".braw", ".r3d", ".crm"}

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac"}

ANALYSIS_SAMPLE_RATE = 48000
DEFAULT_AUDIO_CODEC = "pcm_s16le"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "audiosync.db")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

os.makedirs(STORAGE_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024 * 1024  # 8GB

# SECRET KEY for sessions (change in production, or use env var)
app.secret_key = os.environ.get("AUDIO_SYNC_SECRET_KEY", "dev-secret-change-me")


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            clip_key TEXT,
            filename TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            size_bytes INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()


@app.before_first_request
def _bootstrap_db():
    init_db()


def create_user(email: str, password: str):
    conn = get_db()
    cur = conn.cursor()
    password_hash = generate_password_hash(password)
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    try:
        cur.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email.lower().strip(), password_hash, created_at),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def find_user_by_email(email: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def create_sync_job(user_id: int, clip_key: str, filename: str, storage_path: str, size_bytes: int):
    conn = get_db()
    cur = conn.cursor()
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    cur.execute(
        """
        INSERT INTO sync_jobs (user_id, clip_key, filename, storage_path, size_bytes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, clip_key, filename, storage_path, size_bytes, created_at),
    )
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    return job_id


def get_jobs_for_user(user_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, clip_key, filename, size_bytes, created_at
        FROM sync_jobs
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_job_for_user(job_id: int, user_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM sync_jobs
        WHERE id = ? AND user_id = ?
        """,
        (job_id, user_id),
    )
    row = cur.fetchone()
    conn.close()
    return row


# ============================================================
# FRONTEND (MAIN PAGE HTML)
# ============================================================

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>VIM Media | Audio Sync Service</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <!-- Tailwind -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            watchBlack: "#0a0a0a",
            watchRed: "#e50914",
            watchGold: "#d4af37",
          }
        }
      }
    }
  </script>

  <style>
    body {
      background: radial-gradient(circle at top, #111827 0, #020617 45%, #000000 100%);
      color: #f9fafb;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .spin-slow {
      animation: spin 1.2s linear infinite;
    }
    @keyframes spin {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }
    .progress-stripe {
      background-image: linear-gradient(
        120deg,
        rgba(212, 175, 55, 0.1) 0%,
        rgba(212, 175, 55, 0.8) 40%,
        rgba(212, 175, 55, 0.1) 80%
      );
      background-size: 200% 100%;
      animation: progressMove 1.5s linear infinite;
    }
    @keyframes progressMove {
      from { background-position: 200% 0; }
      to   { background-position: -200% 0; }
    }
  </style>

  <!-- PayPal SDK: AQC5qjaOAHkOLQvTh8fKm_zeV0Wfv9_pUvxk8DQQqUgu6E_KhQVpnJxMKC7MxzM_2PpA3jYpExdJXin5 -->
  <script src="https://www.paypal.com/sdk/js?client-id=AQC5qjaOAHkOLQvTh8fKm_zeV0Wfv9_pUvxk8DQQqUgu6E_KhQVpnJxMKC7MxzM_2PpA3jYpExdJXin5&vault=true&intent=subscription&currency=USD"></script>
</head>
<body class="min-h-screen flex flex-col items-center px-4 py-10 gap-10">

  <!-- MAIN CARD -->
  <div class="w-full max-w-5xl bg-watchBlack/90 border border-white/10 rounded-3xl shadow-2xl backdrop-blur-md p-6 sm:p-8 relative">
    <!-- Header -->
    <header class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <!-- VIM logo -->
        <div class="h-10 flex items-center">
          <img
            src="https://t6ht6kdwnezp05ut.public.blob.vercel-storage.com/WatchVIM%20-%20Content/WatchVIM_New_OTT_Logo.png"
            alt="VIM Media logo"
            class="h-10 w-auto object-contain"
          />
        </div>
        <div>
          <h1 class="text-xl sm:text-2xl font-semibold tracking-tight">
            Audio Sync Service
          </h1>
          <p class="text-xs sm:text-sm text-slate-300">
            Provided by VIM Media, LLC — multi-track, post-ready audio sync for editors.
          </p>
        </div>
      </div>

      <!-- Right header: profile / login shortcut -->
      <div class="flex flex-col items-end gap-1">
        <div class="flex items-center gap-3 text-[11px]">
          <!-- These spans are edited by JS depending on login state -->
          <span id="userStatus" class="text-slate-300"></span>
          <a id="profileLink" href="/profile"
             class="hidden text-watchGold hover:text-white font-semibold">Profile</a>
          <a id="loginLink" href="/login"
             class="text-slate-300 hover:text-watchGold font-semibold">Login</a>
          <a id="signupLink" href="/signup"
             class="text-slate-300 hover:text-watchGold font-semibold">Sign up</a>
          <a id="logoutLink" href="/logout"
             class="hidden text-slate-400 hover:text-red-400 font-semibold">Logout</a>
        </div>
        <a href="#pricing"
           class="inline-flex items-center text-xs font-semibold text-slate-300 hover:text-watchGold">
          View pricing &rsaquo;
        </a>
        <a href="https://watchvim.com" target="_blank"
           class="hidden sm:inline-flex items-center text-xs font-semibold text-watchGold hover:text-white">
          watchvim.com &rsaquo;
        </a>
        <span class="inline-flex items-center gap-1 rounded-full bg-white/5 px-3 py-1 text-[10px] font-medium text-slate-300 border border-white/10">
          <span class="w-1.5 h-1.5 rounded-full bg-watchGold"></span>
          Powered by VIM Media AudioSync v1
        </span>
      </div>
    </header>

    <!-- Description + What this clip will contain -->
    <section class="mb-6 grid gap-4 md:grid-cols-[minmax(0,1.6fr),minmax(0,1.4fr)]">
      <div class="text-sm text-slate-200 space-y-2">
        <p>
          Upload your camera clips and external audio files. This service automatically
          synchronizes waveforms and delivers an edit-ready
          <span class="font-semibold text-watchGold">.mov</span>
          with multiple audio tracks compatible with
          <span class="font-semibold">Adobe Premiere Pro</span> and
          <span class="font-semibold">Final Cut Pro</span>.
        </p>
        <p class="text-xs text-slate-400">
          Clips are grouped by filename prefix (e.g., <code>A001_cam.mp4</code>,
          <code>A001_zoom.wav</code> &rarr; <code>A001_synced.mov</code>).
        </p>
      </div>

      <!-- What this clip will contain -->
      <div class="bg-black/40 border border-white/10 rounded-2xl p-3 sm:p-4 text-xs text-slate-200 space-y-2">
        <h2 class="text-[11px] font-semibold uppercase tracking-wide text-slate-300 mb-1">
          What this clip will contain
        </h2>
        <ul class="space-y-1.5">
          <li class="flex gap-2">
            <span class="mt-[3px] w-1.5 h-1.5 rounded-full bg-watchGold"></span>
            <div>
              <span class="font-semibold text-watchGold">Track 1 – Camera scratch</span><br/>
              <span class="text-slate-400">
                Audio captured directly on the camera body, used as the sync reference.
              </span>
            </div>
          </li>
          <li class="flex gap-2">
            <span class="mt-[3px] w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            <div>
              <span class="font-semibold text-slate-100">Track 2+ – External recorders</span><br/>
              <span class="text-slate-400">
                Each external recorder file becomes its own synced track for mixing.
              </span>
            </div>
          </li>
          <li class="flex gap-2">
            <span class="mt-[3px] w-1.5 h-1.5 rounded-full bg-watchRed"></span>
            <div>
              <span class="font-semibold text-slate-100">Video format</span><br/>
              <span class="text-slate-400">
                Standard footage: original video copied, no re-encode.<br/>
                RAW (.braw / .r3d / .crm): transcoded to a ProRes 422 HQ proxy for smooth editing.
              </span>
            </div>
          </li>
        </ul>
      </div>
    </section>

    <!-- File summary + Upload / Pay-per-job -->
    <section class="grid gap-5 lg:grid-cols-[minmax(0,1.4fr),minmax(0,1.1fr)] items-start">
      <!-- Left: upload & status -->
      <div>
        <!-- File summary -->
        <div class="mb-4">
          <h2 class="text-xs font-semibold text-slate-300 uppercase tracking-wide mb-1">
            Selected files
          </h2>
          <div id="fileList" class="text-xs text-slate-400 border border-white/5 rounded-lg p-3 min-h-[3rem] bg-black/30">
            <span class="text-slate-500">No files selected yet.</span>
          </div>
        </div>

        <!-- Upload Form -->
        <form id="uploadForm" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1">Upload media</label>
            <input id="files" name="files" type="file" multiple
                   class="block w-full text-sm text-slate-100
                          file:mr-3 file:py-2 file:px-4
                          file:rounded-md file:border-0
                          file:text-sm file:font-semibold
                          file:bg-watchRed file:text-white
                          hover:file:bg-red-700
                          cursor-pointer" />
            <p class="mt-2 text-xs text-slate-400">
              Include camera video (.mp4, .mov, .mxf, .braw, .r3d, .crm) and matching
              external audio (.wav, .mp3, .m4a, etc.). Use matching prefixes
              (e.g. <code>SC01_T01_cam.mp4</code> and <code>SC01_T01_zoom.wav</code>).
            </p>
          </div>

          <button id="syncButton" type="submit"
                  class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-full
                         bg-watchGold text-black text-sm font-semibold
                         hover:bg-yellow-400 transition disabled:opacity-60 disabled:cursor-not-allowed">
            <span>Sync &amp; Download</span>
          </button>

          <div id="status" class="mt-2 text-xs sm:text-sm text-slate-300 min-h-[1.5rem]"></div>
        </form>
      </div>

      <!-- Right: Pay-per-job -->
      <div class="bg-black/40 border border-watchGold/20 rounded-2xl p-4 space-y-3">
        <h3 class="text-sm font-semibold text-watchGold">
          Pay-per-job · $7 per sync
        </h3>
        <p class="text-xs text-slate-300">
          Don&apos;t need a monthly plan yet? Pay once per job and let VIM Media handle
          the sync work for this upload.
        </p>

        <div class="text-[11px] text-slate-400 space-y-1">
          <p>Includes:</p>
          <ul class="list-disc pl-4 space-y-0.5">
            <li>One synced multi-track <code>.mov</code> (or ZIP for multiple clips)</li>
            <li>Support for standard &amp; RAW formats</li>
            <li>Scratch + external tracks for mixing in your NLE</li>
          </ul>
        </div>

        <div class="mt-2">
          <div id="paypal-button-container"></div>
          <p id="paymentStatus" class="mt-2 text-[11px] text-slate-400">
            Complete payment to unlock syncing for this job.
          </p>
        </div>

        <p class="text-[11px] text-slate-500 border-t border-white/10 pt-3 mt-2">
          Already on an Indie / Studio / Pro plan? Use the subscription options below
          so you don&apos;t have to pay per job.
        </p>
      </div>
    </section>

    <!-- Footer -->
    <footer class="mt-6 border-t border-white/10 pt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
      <p class="text-[11px] text-slate-400">
        &copy; <span id="year"></span> VIM Media, LLC. All rights reserved.
      </p>
      <p class="text-[11px] text-slate-500">
        Built for post-production teams who live in timelines, bins, and multitrack madness.
      </p>
    </footer>

    <!-- Processing overlay -->
    <div id="processingOverlay"
         class="hidden absolute inset-0 rounded-3xl bg-black/80 backdrop-blur-md flex flex-col items-center justify-center z-20">
      <div class="flex flex-col items-center gap-4 px-6 text-center max-w-sm">
        <div class="flex items-center justify-center gap-3">
          <div class="h-9 flex items-center">
            <img
              src="https://t6ht6kdwnezp05ut.public.blob.vercel-storage.com/WatchVIM%20-%20Content/WatchVIM_New_OTT_Logo.png"
              alt="VIM Media logo small"
              class="h-9 w-auto object-contain"
            />
          </div>
          <span class="text-sm font-semibold text-slate-100">
            Syncing with VIM Media
          </span>
        </div>

        <div class="w-10 h-10 rounded-full border border-watchGold/60 border-t-transparent spin-slow"></div>

        <div class="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
          <div class="w-2/3 h-full progress-stripe"></div>
        </div>

        <div>
          <p id="processingStep" class="text-sm font-semibold text-slate-100">
            Preparing upload…
          </p>
          <p id="processingSub" class="mt-1 text-xs text-slate-300">
            This can take a few minutes for 4K or RAW footage. Please keep this tab open.
          </p>
        </div>
      </div>
    </div>
  </div>

  <!-- PRICING SECTION -->
  <section id="pricing" class="w-full max-w-5xl">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="text-lg sm:text-xl font-semibold text-slate-100">
          Pricing built for indie creators up to full studios
        </h2>
        <p class="text-xs sm:text-sm text-slate-400">
          Start with Pay-per-job or move into monthly tiers as your pipeline grows.
        </p>
      </div>
    </div>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <!-- Indie Creator -->
      <div class="bg-watchBlack/90 border border-white/10 rounded-2xl p-4 flex flex-col justify-between">
        <div class="space-y-1">
          <h3 class="text-sm font-semibold text-slate-100">Indie Creator</h3>
          <p class="text-xl font-bold text-watchGold">$24<span class="text-xs text-slate-400">/month</span></p>
          <p class="text-[11px] text-slate-400">
            For solo editors, micro-budget films, and YouTubers.
          </p>
          <ul class="mt-2 text-[11px] text-slate-300 space-y-1">
            <li>Up to 50 sync jobs / month</li>
            <li>~300 GB transfer</li>
            <li>Standard processing priority</li>
            <li>Up to 6 audio tracks per clip</li>
          </ul>
        </div>
        <div class="mt-3">
          <div id="paypal-indie-sub"></div>
          <p class="mt-2 text-[11px] text-slate-500">
            Subscribe with PayPal. No separate VIM account needed yet.
          </p>
        </div>
      </div>

      <!-- Studio -->
      <div class="bg-watchBlack/90 border border-watchGold/60 rounded-2xl p-4 flex flex-col justify-between">
        <div class="space-y-1">
          <h3 class="text-sm font-semibold text-slate-100">Studio</h3>
          <p class="text-xl font-bold text-watchGold">$79<span class="text-xs text-slate-400">/month</span></p>
          <p class="text-[11px] text-slate-400">
            For boutique production companies and small agencies.
          </p>
          <ul class="mt-2 text-[11px] text-slate-300 space-y-1">
            <li>Up to 250 sync jobs / month</li>
            <li>~1 TB transfer</li>
            <li>Higher queue priority</li>
            <li>3–5 team seats</li>
          </ul>
        </div>
        <div class="mt-3">
          <div id="paypal-studio-sub"></div>
          <p class="mt-2 text-[11px] text-slate-500">
            Subscribe with PayPal for recurring studio usage.
          </p>
        </div>
      </div>

      <!-- Pro Studio -->
      <div class="bg-watchBlack/90 border border-white/10 rounded-2xl p-4 flex flex-col justify-between">
        <div class="space-y-1">
          <h3 class="text-sm font-semibold text-slate-100">Pro Studio</h3>
          <p class="text-xl font-bold text-watchGold">$199<span class="text-xs text-slate-400">/month</span></p>
          <p class="text-[11px] text-slate-400">
            For serious series work, agency pipelines, and high-volume teams.
          </p>
          <ul class="mt-2 text-[11px] text-slate-300 space-y-1">
            <li>Up to 750 sync jobs / month</li>
            <li>5+ TB transfer</li>
            <li>Highest shared priority</li>
            <li>Up to 15 seats + API access</li>
          </ul>
        </div>
        <div class="mt-3">
          <div id="paypal-pro-sub"></div>
          <p class="mt-2 text-[11px] text-slate-500">
            Subscribe with PayPal for Pro-level volume.
          </p>
        </div>
      </div>

      <!-- Enterprise -->
      <div class="bg-watchBlack/90 border border-white/10 rounded-2xl p-4 flex flex-col justify-between">
        <div class="space-y-1">
          <h3 class="text-sm font-semibold text-slate-100">Enterprise</h3>
          <p class="text-xl font-bold text-watchGold">Let&apos;s talk</p>
          <p class="text-[11px] text-slate-400">
            For networks, OTT platforms, post houses, and cloud MAM vendors.
          </p>
          <ul class="mt-2 text-[11px] text-slate-300 space-y-1">
            <li>Custom volume &amp; private infrastructure</li>
            <li>SSO / SAML, SLAs, dedicated support</li>
            <li>Integrations &amp; custom feature work</li>
          </ul>
        </div>
        <a href="mailto:streaming@watchvim.com?subject=Enterprise%20AudioSync"
           class="mt-3 inline-flex justify-center rounded-full border border-slate-500 px-3 py-1.5 text-[11px] font-semibold text-slate-200 hover:bg-slate-200 hover:text-black">
          Contact VIM for Enterprise
        </a>
      </div>
    </div>
  </section>

  <script>
    document.getElementById('year').textContent = new Date().getFullYear();

    // ===== Payment config =====
    const PAYMENT_REQUIRED = false;      // set false to test without PayPal
    const PAY_PER_JOB_AMOUNT = "7.00";

    const INDIE_PLAN_ID  = "P-5HF24724VN545651WNEZ6SDQ";
    const STUDIO_PLAN_ID = "P-7W490604V8434754DNEZ6TAA";
    const PRO_PLAN_ID    = "P-4KL402168F127405GNEZ6TWY";

    const form = document.getElementById('uploadForm');
    const statusEl = document.getElementById('status');
    const filesInput = document.getElementById('files');
    const fileListEl = document.getElementById('fileList');
    const syncButton = document.getElementById('syncButton');
    const overlay = document.getElementById('processingOverlay');
    const processingStep = document.getElementById('processingStep');
    const processingSub = document.getElementById('processingSub');
    const paymentStatusEl = document.getElementById('paymentStatus');

    const userStatusEl = document.getElementById('userStatus');
    const profileLink = document.getElementById('profileLink');
    const loginLink = document.getElementById('loginLink');
    const signupLink = document.getElementById('signupLink');
    const logoutLink = document.getElementById('logoutLink');

    let overlayTimer = null;
    let isProcessing = false;
    let hasPaid = !PAYMENT_REQUIRED;

    // This flag is injected via cookie by backend using a tiny trick:
    // we can't see Flask session directly, but we can expose a header
    // later if you want. For now, we just show generic text.
    // (If you later add an API to expose logged-in email, update this.)
    userStatusEl.textContent = '';

    if (PAYMENT_REQUIRED) {
      syncButton.disabled = true;
      paymentStatusEl.textContent = 'Complete payment to unlock syncing for this job.';
    } else {
      paymentStatusEl.textContent = 'Payment is disabled in this environment (testing mode).';
    }

    function renderFileList(files) {
      if (!files.length) {
        fileListEl.innerHTML = '<span class="text-slate-500">No files selected yet.</span>';
        return;
      }
      const items = [];
      for (const f of files) {
        items.push(
          '<li class="flex justify-between gap-3">' +
            '<span class="truncate max-w-[14rem]">' + f.name + '</span>' +
            '<span class="text-slate-500">' + (f.size / (1024*1024)).toFixed(1) + ' MB</span>' +
          '</li>'
        );
      }
      fileListEl.innerHTML = '<ul class="space-y-1">' + items.join("") + '</ul>';
    }

    filesInput.addEventListener('change', () => {
      renderFileList(filesInput.files);
    });

    function setOverlayStep(step, sub) {
      processingStep.textContent = step;
      if (sub) processingSub.textContent = sub;
    }

    function showOverlay() {
      isProcessing = true;
      overlay.classList.remove('hidden');

      const steps = [
        ['Step 1/3: Uploading your media…', 'Large RAW and 4K files may take a little longer to reach our servers.'],
        ['Step 2/3: Syncing audio & video waveforms…', 'We analyze camera scratch audio and your external recordings to find the best alignment.'],
        ['Step 3/3: Building your multi-track .mov…', 'Creating an edit-ready file with separate tracks for scratch and external audio.'],
      ];
      let idx = 0;
      setOverlayStep(steps[0][0], steps[0][1]);

      if (overlayTimer) clearInterval(overlayTimer);
      overlayTimer = setInterval(() => {
        if (!isProcessing) {
          clearInterval(overlayTimer);
          return;
        }
        idx = (idx + 1) % steps.length;
        setOverlayStep(steps[idx][0], steps[idx][1]);
      }, 6000);
    }

    function hideOverlay() {
      isProcessing = false;
      overlay.classList.add('hidden');
      if (overlayTimer) clearInterval(overlayTimer);
    }

    // ===== PayPal: Pay-per-job button =====
    if (window.paypal && PAYMENT_REQUIRED) {
      paypal.Buttons({
        style: {
          layout: 'horizontal',
          color: 'gold',
          shape: 'pill',
          label: 'pay'
        },
        createOrder: function(data, actions) {
          return actions.order.create({
            purchase_units: [{
              description: 'VIM Media AudioSync Pay-per-Job',
              amount: { value: PAY_PER_JOB_AMOUNT }
            }]
          });
        },
        onApprove: function(data, actions) {
          return actions.order.capture().then(function(details) {
            hasPaid = true;
            syncButton.disabled = false;
            paymentStatusEl.textContent = 'Payment received. You can now upload and sync this job.';
          });
        },
        onCancel: function() {
          paymentStatusEl.textContent = 'Payment cancelled. You can try again when ready.';
        },
        onError: function(err) {
          console.error(err);
          paymentStatusEl.textContent = 'There was an error with PayPal. Please try again.';
        }
      }).render('#paypal-button-container');
    } else if (!PAYMENT_REQUIRED) {
      paymentStatusEl.textContent = 'Payment is disabled in this environment (testing mode).';
    }

    // ===== PayPal: Subscription buttons (Indie / Studio / Pro) =====
    if (window.paypal) {
      if (INDIE_PLAN_ID && INDIE_PLAN_ID !== "P-INDIE_PLAN_ID_HERE") {
        paypal.Buttons({
          style: { color: 'gold', shape: 'pill', label: 'subscribe' },
          createSubscription: function(data, actions) {
            return actions.subscription.create({
              plan_id: INDIE_PLAN_ID
            });
          },
          onApprove: function(data, actions) {
            alert('Thank you for subscribing to Indie Creator! (Subscription ID: ' + data.subscriptionID + ')');
          },
          onError: function(err) {
            console.error(err);
          }
        }).render('#paypal-indie-sub');
      }

      if (STUDIO_PLAN_ID && STUDIO_PLAN_ID !== "P-STUDIO_PLAN_ID_HERE") {
        paypal.Buttons({
          style: { color: 'gold', shape: 'pill', label: 'subscribe' },
          createSubscription: function(data, actions) {
            return actions.subscription.create({
              plan_id: STUDIO_PLAN_ID
            });
          },
          onApprove: function(data, actions) {
            alert('Thank you for subscribing to Studio! (Subscription ID: ' + data.subscriptionID + ')');
          },
          onError: function(err) {
            console.error(err);
          }
        }).render('#paypal-studio-sub');
      }

      if (PRO_PLAN_ID && PRO_PLAN_ID !== "P-PRO_PLAN_ID_HERE") {
        paypal.Buttons({
          style: { color: 'gold', shape: 'pill', label: 'subscribe' },
          createSubscription: function(data, actions) {
            return actions.subscription.create({
              plan_id: PRO_PLAN_ID
            });
          },
          onApprove: function(data, actions) {
            alert('Thank you for subscribing to Pro Studio! (Subscription ID: ' + data.subscriptionID + ')');
          },
          onError: function(err) {
            console.error(err);
          }
        }).render('#paypal-pro-sub');
      }
    }

    // ===== Upload & sync handler =====
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (!filesInput.files.length) {
        alert('Please select at least one file.');
        return;
      }

      if (!hasPaid) {
        alert('Please complete the Pay-per-job payment before syncing.');
        return;
      }

      statusEl.textContent = 'Uploading & syncing… please keep this tab open.';
      showOverlay();

      const formData = new FormData();
      for (const f of filesInput.files) {
        formData.append('files', f);
      }

      try {
        const res = await fetch('/sync', {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const text = await res.text();
          hideOverlay();
          statusEl.textContent = 'Error: ' + text;
          return;
        }

        setOverlayStep('Finishing up…', 'Packaging your synced media and starting the download.');

        const blob = await res.blob();
        const disposition = res.headers.get('Content-Disposition') || '';
        let filename = 'synced_output';
        const match = disposition.match(/filename="?([^"]+)"?/i);
        if (match && match[1]) {
          filename = match[1];
        }

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        hideOverlay();
        statusEl.textContent = 'Done! Your synced file(s) should begin downloading automatically.';
      } catch (err) {
        console.error(err);
        hideOverlay();
        statusEl.textContent = 'Unexpected error. Please try again or contact VIM Media support.';
      }
    });
  </script>
</body>
</html>
"""


# ============================================================
# SIMPLE AUTH HTML (SIGNUP / LOGIN / PROFILE)
# ============================================================

def render_auth_page(title: str, action_url: str, button_label: str, error: str = ""):
    error_html = ""
    if error:
        error_html = f'<p class="mt-2 text-xs text-red-400">{error}</p>'

    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{title} · VIM AudioSync</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            watchBlack: "#0a0a0a",
            watchRed: "#e50914",
            watchGold: "#d4af37",
          }}
        }}
      }}
    }}
  </script>
</head>
<body class="min-h-screen bg-watchBlack text-slate-100 flex items-center justify-center px-4">
  <div class="w-full max-w-md bg-black/80 border border-white/10 rounded-2xl p-6 space-y-4 shadow-2xl">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <img
          src="https://t6ht6kdwnezp05ut.public.blob.vercel-storage.com/WatchVIM%20-%20Content/WatchVIM_New_OTT_Logo.png"
          alt="VIM Media"
          class="h-8 w-auto"
        />
        <span class="text-xs text-slate-400 uppercase tracking-wide">AudioSync</span>
      </div>
      <a href="/" class="text-xs text-slate-400 hover:text-watchGold">Back to sync</a>
    </div>

    <h1 class="text-xl font-semibold">{title}</h1>

    <form method="post" action="{action_url}" class="space-y-4">
      <div>
        <label class="block text-xs font-semibold mb-1">Email</label>
        <input type="email" name="email" required
               class="w-full rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-watchGold" />
      </div>
      <div>
        <label class="block text-xs font-semibold mb-1">Password</label>
        <input type="password" name="password" required
               class="w-full rounded-md bg-slate-900 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-watchGold" />
      </div>
      {error_html}
      <button type="submit"
              class="w-full inline-flex items-center justify-center rounded-full bg-watchGold text-black text-sm font-semibold py-2 hover:bg-yellow-400">
        {button_label}
      </button>
    </form>
  </div>
</body>
</html>
"""


def render_profile_page(user_email: str, jobs):
    rows_html = ""
    if not jobs:
        rows_html = """
          <tr>
            <td colspan="4" class="px-3 py-4 text-center text-xs text-slate-500">
              No sync history yet. Run your first job from the main AudioSync page.
            </td>
          </tr>
        """
    else:
        for job in jobs:
            size_mb = (job["size_bytes"] or 0) / (1024 * 1024)
            clip = job["clip_key"] or "-"
            rows_html += f"""
              <tr class="border-t border-white/5">
                <td class="px-3 py-2 text-xs text-slate-200">{job['created_at']}</td>
                <td class="px-3 py-2 text-xs text-slate-300">{clip}</td>
                <td class="px-3 py-2 text-xs text-slate-300">{job['filename']}</td>
                <td class="px-3 py-2 text-xs text-slate-300">
                  {size_mb:.1f} MB
                  <a href="/download/{job['id']}"
                     class="ml-3 text-[11px] text-watchGold hover:text-white underline">
                    Download
                  </a>
                </td>
              </tr>
            """

    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Profile · VIM AudioSync</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            watchBlack: "#0a0a0a",
            watchRed: "#e50914",
            watchGold: "#d4af37",
          }}
        }}
      }}
    }}
  </script>
</head>
<body class="min-h-screen bg-watchBlack text-slate-100 px-4 py-8">
  <div class="max-w-5xl mx-auto space-y-6">
    <header class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <img
          src="https://t6ht6kdwnezp05ut.public.blob.vercel-storage.com/WatchVIM%20-%20Content/WatchVIM_New_OTT_Logo.png"
          alt="VIM Media"
          class="h-9 w-auto"
        />
        <div>
          <h1 class="text-lg font-semibold">Your AudioSync profile</h1>
          <p class="text-xs text-slate-400">{user_email}</p>
        </div>
      </div>
      <div class="flex flex-col items-end gap-1">
        <a href="/" class="text-xs text-slate-300 hover:text-watchGold">Back to sync</a>
        <a href="/logout" class="text-xs text-slate-400 hover:text-red-400">Logout</a>
      </div>
    </header>

    <section class="bg-black/70 border border-white/10 rounded-2xl p-4">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-slate-100">Previous sync jobs</h2>
        <p class="text-[11px] text-slate-400">
          Files listed here are separate from watchvim.com and stored only for your AudioSync account.
        </p>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-xs">
          <thead class="bg-white/5">
            <tr>
              <th class="px-3 py-2 font-semibold text-slate-300">Date</th>
              <th class="px-3 py-2 font-semibold text-slate-300">Clip key</th>
              <th class="px-3 py-2 font-semibold text-slate-300">File</th>
              <th class="px-3 py-2 font-semibold text-slate-300">Size &amp; Download</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </div>
    </section>
  </div>
</body>
</html>
"""


# ============================================================
# SYNC LOGIC (FFMPEG, WAV, ETC.)
# ============================================================

def ensure_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg on your server.")


def run_ffmpeg(args):
    cmd = ["ffmpeg", "-y"] + args
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print("FFmpeg error:", proc.stderr)
        raise RuntimeError("ffmpeg command failed")


def extract_mono_wav(input_path: str, output_path: str, sample_rate: int = ANALYSIS_SAMPLE_RATE):
    run_ffmpeg([
        "-i", input_path,
        "-ac", "1",
        "-ar", str(sample_rate),
        "-vn",
        output_path,
    ])


def load_audio_mono(path: str):
    data, sr = sf.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float32)
    return data, sr


def estimate_offset_seconds(cam_audio: np.ndarray,
                            ext_audio: np.ndarray,
                            sample_rate: int) -> float:
    cam = cam_audio.astype(np.float32)
    ext = ext_audio.astype(np.float32)

    cam -= cam.mean()
    ext -= ext.mean()
    cam /= (cam.std() + 1e-9)
    ext /= (ext.std() + 1e-9)

    corr = correlate(cam, ext, mode="full", method="fft")
    lags = np.arange(-len(ext) + 1, len(cam))
    best_lag = lags[np.argmax(corr)]

    offset_seconds = -best_lag / float(sample_rate)
    return offset_seconds


def build_aligned_external(cam_audio: np.ndarray,
                           ext_audio: np.ndarray,
                           sample_rate: int,
                           offset_seconds: float) -> np.ndarray:
    n_cam = len(cam_audio)
    ext = ext_audio.astype(np.float32)

    if offset_seconds >= 0:
        pad_samples = int(round(offset_seconds * sample_rate))
        aligned = np.zeros(n_cam, dtype=np.float32)
        start = pad_samples
        if start >= n_cam:
            return aligned
        end = min(n_cam, start + len(ext))
        aligned[start:end] = ext[: end - start]
    else:
        lead_samples = int(round(-offset_seconds * sample_rate))
        if lead_samples >= len(ext):
            return np.zeros(n_cam, dtype=np.float32)
        trimmed = ext[lead_samples:]
        aligned = np.zeros(n_cam, dtype=np.float32)
        end = min(n_cam, len(trimmed))
        aligned[:end] = trimmed[:end]

    return aligned


def process_clip_to_multitrack_mov(video_path: str,
                                   external_audio_paths,
                                   output_path: str,
                                   sample_rate: int = ANALYSIS_SAMPLE_RATE):
    ensure_ffmpeg()

    with tempfile.TemporaryDirectory() as workdir:
        cam_wav = os.path.join(workdir, "cam.wav")
        extract_mono_wav(video_path, cam_wav, sample_rate)
        cam_audio, sr_cam = load_audio_mono(cam_wav)

        aligned_paths = []

        for idx, ext_path in enumerate(external_audio_paths):
            ext_wav = os.path.join(workdir, f"ext_{idx}.wav")
            extract_mono_wav(ext_path, ext_wav, sample_rate)
            ext_audio, sr_ext = load_audio_mono(ext_wav)

            if sr_cam != sr_ext:
                raise RuntimeError(f"Sample rate mismatch cam={sr_cam}, ext={sr_ext} after conversion")

            offset = estimate_offset_seconds(cam_audio, ext_audio, sr_cam)
            print(f"[Clip] {os.path.basename(video_path)} / "
                  f"{os.path.basename(ext_path)} offset: {offset:.3f} s")

            aligned_ext = build_aligned_external(cam_audio, ext_audio, sr_cam, offset)
            aligned_wav = os.path.join(workdir, f"ext_{idx}_aligned.wav")
            sf.write(aligned_wav, aligned_ext, sr_cam, subtype="PCM_16")
            aligned_paths.append(aligned_wav)

        args = ["-i", video_path]
        for ap in aligned_paths:
            args += ["-i", ap]

        args += [
            "-map", "0:v:0",
            "-map", "0:a:0",
        ]
        for i in range(len(aligned_paths)):
            args += ["-map", f"{i + 1}:a:0"]

        ext = os.path.splitext(video_path)[1].lower()
        is_raw = ext in RAW_VIDEO_EXTS

        if is_raw:
            args += [
                "-c:v", "prores_ks",
                "-profile:v", "3",
                "-pix_fmt", "yuv422p10le",
            ]
        else:
            args += ["-c:v", "copy"]

        args += [
            "-c:a", DEFAULT_AUDIO_CODEC,
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]

        run_ffmpeg(args)


def classify_and_group_files(temp_dir, uploaded_files):
    clips = {}

    for storage in uploaded_files:
        filename = secure_filename(storage.filename or "")
        if not filename:
            continue

        ext = os.path.splitext(filename)[1].lower()
        dest_path = os.path.join(temp_dir, filename)
        storage.save(dest_path)

        base = os.path.splitext(filename)[0]
        clip_key = base.split("_")[0]

        clip = clips.setdefault(clip_key, {"videos": [], "audios": []})

        if ext in VIDEO_EXTS:
            clip["videos"].append(dest_path)
        elif ext in AUDIO_EXTS:
            clip["audios"].append(dest_path)

    return clips


# ============================================================
# ROUTES: MAIN, AUTH, PROFILE, DOWNLOAD, SYNC
# ============================================================

@app.route("/", methods=["GET"])
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return Response(
            render_auth_page("Sign up for AudioSync", "/signup", "Create account"),
            mimetype="text/html",
        )

    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    if not email or not password:
        return Response(
            render_auth_page("Sign up for AudioSync", "/signup", "Create account", "Email and password are required."),
            mimetype="text/html",
        )

    existing = find_user_by_email(email)
    if existing:
        return Response(
            render_auth_page("Sign up for AudioSync", "/signup", "Create account", "That email is already registered."),
            mimetype="text/html",
        )

    user_id = create_user(email, password)
    if not user_id:
        return Response(
            render_auth_page("Sign up for AudioSync", "/signup", "Create account", "Could not create account. Try again."),
            mimetype="text/html",
        )

    session["user_id"] = user_id
    session["user_email"] = email
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return Response(
            render_auth_page("Log in to AudioSync", "/login", "Log in"),
            mimetype="text/html",
        )

    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    user = find_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return Response(
            render_auth_page("Log in to AudioSync", "/login", "Log in", "Invalid email or password."),
            mimetype="text/html",
        )

    session["user_id"] = user["id"]
    session["user_email"] = user["email"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    user_email = session.get("user_email")

    if not user_id or not user_email:
        return redirect(url_for("login"))

    jobs = get_jobs_for_user(user_id)
    html = render_profile_page(user_email, jobs)
    return Response(html, mimetype="text/html")


@app.route("/download/<int:job_id>")
def download(job_id: int):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    job = get_job_for_user(job_id, user_id)
    if not job:
        return "Not found or not authorized", 404

    path = job["storage_path"]
    if not os.path.isfile(path):
        return "File no longer available on server", 404

    return send_file(
        path,
        as_attachment=True,
        download_name=job["filename"],
        mimetype="video/quicktime",
    )


@app.route("/sync", methods=["POST"])
def sync_route():
    files = request.files.getlist("files")
    if not files:
        return "No files uploaded", 400

    tmpdir = tempfile.mkdtemp(prefix="vimmedia_audiosync_")
    outputs = []

    try:
        clips = classify_and_group_files(tmpdir, files)

        for clip_key, clip_data in clips.items():
            videos = clip_data["videos"]
            audios = clip_data["audios"]

            if not videos or not audios:
                continue

            video_path = videos[0]
            ext_paths = audios

            out_name = f"{clip_key}_synced.mov"
            out_path = os.path.join(tmpdir, out_name)

            process_clip_to_multitrack_mov(video_path, ext_paths, out_path)
            outputs.append((clip_key, out_path))

        if not outputs:
            return (
                "No valid clip groups found. Each clip needs at least one video and one audio file "
                "with matching prefixes (e.g., SC01_T01_cam.mp4 & SC01_T01_zoom.wav).",
                400,
            )

        # If user is logged in, copy outputs to persistent storage and record jobs
        user_id = session.get("user_id")
        if user_id:
            user_dir = os.path.join(STORAGE_DIR, str(user_id))
            os.makedirs(user_dir, exist_ok=True)

            for clip_key, temp_out in outputs:
                filename = os.path.basename(temp_out)
                dest_path = os.path.join(user_dir, filename)
                shutil.copy2(temp_out, dest_path)
                size_bytes = os.path.getsize(dest_path)
                create_sync_job(user_id, clip_key, filename, dest_path, size_bytes)

        # Response: single file or zip (same as before)
        if len(outputs) == 1:
            clip_key, out_path = outputs[0]
            return send_file(
                out_path,
                as_attachment=True,
                download_name=os.path.basename(out_path),
                mimetype="video/quicktime",
            )
        else:
            zip_path = os.path.join(tmpdir, "synced_clips.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for clip_key, op in outputs:
                    zf.write(op, arcname=os.path.basename(op))

            return send_file(
                zip_path,
                as_attachment=True,
                download_name="synced_clips.zip",
                mimetype="application/zip",
            )
    finally:
        # temp dir will be cleaned up eventually; explicit cleanup optional here
        pass


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
