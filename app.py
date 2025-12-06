#!/usr/bin/env python3
"""
VIM Media | Audio Sync Service

Web-based tool to:
- Upload multiple camera clips + external audio
- Support standard formats + RAW (.braw, .r3d, .crm)
- Sync via waveform cross-correlation
- Export multi-track .mov ready for Adobe Premiere Pro & Final Cut Pro

Provided as a service by VIM Media, LLC.
"""

import os
import shutil
import subprocess
import tempfile
import zipfile

from flask import Flask, request, send_file, Response
from werkzeug.utils import secure_filename

import numpy as np
import soundfile as sf
from scipy.signal import correlate


# ============================================================
# CONFIG
# ============================================================

# Video formats we accept
VIDEO_EXTS = {
    ".mp4", ".mov", ".mxf", ".avi", ".mkv",
    ".braw",  # Blackmagic RAW
    ".r3d",   # RED RAW
    ".crm",   # Canon Cinema RAW
}

# RAW formats that get proxied to ProRes 422 HQ
RAW_VIDEO_EXTS = {".braw", ".r3d", ".crm"}

# Audio formats we accept
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac"}

ANALYSIS_SAMPLE_RATE = 48000  # standard video-post sample rate
DEFAULT_AUDIO_CODEC = "pcm_s16le"  # uncompressed PCM

# Payment settings (front-end gating only)
PAY_PER_JOB_AMOUNT = "7.00"  # USD
PAYMENT_REQUIRED = True      # set to False to disable gating while testing

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024 * 1024  # 8GB


# ============================================================
# FRONTEND (VIM Media branded, pricing + PayPal)
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

  <!-- PayPal SDK (AQC5qjaOAHkOLQvTh8fKm_zeV0Wfv9_pUvxk8DQQqUgu6E_KhQVpnJxMKC7MxzM_2PpA3jYpExdJXin5) -->
  <script src="https://www.paypal.com/sdk/js?client-id=AQC5qjaOAHkOLQvTh8fKm_zeV0Wfv9_pUvxk8DQQqUgu6E_KhQVpnJxMKC7MxzM_2PpA3jYpExdJXin5&currency=USD"></script>
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

      <div class="flex flex-col items-end gap-1">
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
      <!-- Left: upload & PayPal -->
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

      <!-- Right: Pay-per-job + explainer -->
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
            <li>Support for standard & RAW formats</li>
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
          Already on an Indie / Studio / Pro plan? You&apos;ll soon be able to log in
          and sync without Pay-per-job. For now, teams can contact
          <a href="mailto:streaming@watchvim.com" class="underline hover:text-watchGold">
            streaming@watchvim.com
          </a>
          for studio access.
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
        <a href="mailto:streaming@watchvim.com?subject=Indie%20Creator%20AudioSync"
           class="mt-3 inline-flex justify-center rounded-full border border-watchGold/80 px-3 py-1.5 text-[11px] font-semibold text-watchGold hover:bg-watchGold hover:text-black">
          Talk to VIM about Indie
        </a>
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
        <a href="mailto:streaming@watchvim.com?subject=Studio%20AudioSync"
           class="mt-3 inline-flex justify-center rounded-full bg-watchGold px-3 py-1.5 text-[11px] font-semibold text-black hover:bg-yellow-400">
          Talk to VIM about Studio
        </a>
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
        <a href="mailto:streaming@watchvim.com?subject=Pro%20Studio%20AudioSync"
           class="mt-3 inline-flex justify-center rounded-full border border-watchGold/80 px-3 py-1.5 text-[11px] font-semibold text-watchGold hover:bg-watchGold hover:text-black">
          Talk to VIM about Pro Studio
        </a>
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

    const PAYMENT_REQUIRED = %s;  // injected below from Python
    const form = document.getElementById('uploadForm');
    const statusEl = document.getElementById('status');
    const filesInput = document.getElementById('files');
    const fileListEl = document.getElementById('fileList');
    const syncButton = document.getElementById('syncButton');
    const overlay = document.getElementById('processingOverlay');
    const processingStep = document.getElementById('processingStep');
    const processingSub = document.getElementById('processingSub');
    const paymentStatusEl = document.getElementById('paymentStatus');

    let overlayTimer = null;
    let isProcessing = false;
    let hasPaid = !PAYMENT_REQUIRED;  // if payment not required, treat as paid

    // Initial sync button state
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

    // PayPal buttons (guarded in case SDK fails to load)
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
              amount: { value: '%s' }
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
""" % ("true" if PAYMENT_REQUIRED else "false", PAY_PER_JOB_AMOUNT)


# ============================================================
# CORE SYNC LOGIC
# ============================================================

def ensure_ffmpeg():
    """Ensure ffmpeg is installed and on PATH."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg on your server.")


def run_ffmpeg(args):
    """Run ffmpeg with -y and provided args; raise on error."""
    cmd = ["ffmpeg", "-y"] + args
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print("FFmpeg error:", proc.stderr)
        raise RuntimeError("ffmpeg command failed")


def extract_mono_wav(input_path: str, output_path: str, sample_rate: int = ANALYSIS_SAMPLE_RATE):
    """Extract / convert audio from any media to mono WAV at a fixed sample rate."""
    run_ffmpeg([
        "-i", input_path,
        "-ac", "1",
        "-ar", str(sample_rate),
        "-vn",
        output_path,
    ])


def load_audio_mono(path: str):
    """Load mono WAV as float32 numpy array and sample rate."""
    data, sr = sf.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float32)
    return data, sr


def estimate_offset_seconds(cam_audio: np.ndarray,
                            ext_audio: np.ndarray,
                            sample_rate: int) -> float:
    """
    Estimate time offset between camera audio and external audio via cross-correlation.

    Returns offset in seconds:
      > 0: external starts later than camera
      < 0: external starts earlier than camera
    """
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
    """
    Build external audio waveform aligned to camera audio length.
    """
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
    """
    For a single clip:
      - Extract camera onboard audio
      - Align each external audio file
      - Mux into a multi-track .mov

      Non-RAW:
        -c:v copy (video untouched)
        -c:a pcm_s16le (multi-track audio)

      RAW (.braw, .r3d, .crm):
        -c:v prores_ks -profile:v 3 (ProRes 422 HQ proxy)
        -c:a pcm_s16le
    """
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
            "-map", "0:v:0",  # camera video
            "-map", "0:a:0",  # camera scratch audio (if present)
        ]
        for i in range(len(aligned_paths)):
            args += ["-map", f"{i + 1}:a:0"]  # aligned externals

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
    """
    Save uploads to temp_dir, classify by extension, then group into clips.

    Clips are grouped by filename prefix before first underscore.
      Example:
        A001_cam.mp4  -> key A001
        A001_zoom.wav -> key A001
    """
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
        else:
            # ignore unknown types
            pass

    return clips


# ============================================================
# ROUTES
# ============================================================

@app.route("/", methods=["GET"])
def index():
    return Response(INDEX_HTML, mimetype="text/html")


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
            outputs.append(out_path)

        if not outputs:
            return (
                "No valid clip groups found. Each clip needs at least one video and one audio file "
                "with matching prefixes (e.g., SC01_T01_cam.mp4 & SC01_T01_zoom.wav).",
                400,
            )

        if len(outputs) == 1:
            out_path = outputs[0]
            return send_file(
                out_path,
                as_attachment=True,
                download_name=os.path.basename(out_path),
                mimetype="video/quicktime",
            )
        else:
            zip_path = os.path.join(tmpdir, "synced_clips.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for op in outputs:
                    zf.write(op, arcname=os.path.basename(op))

            return send_file(
                zip_path,
                as_attachment=True,
                download_name="synced_clips.zip",
                mimetype="application/zip",
            )

    finally:
        # OS will eventually clean up temp dirs; explicit cleanup can be added later.
        pass


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    # Dev mode
    app.run(host="0.0.0.0", port=5000, debug=True)
