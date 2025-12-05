#!/usr/bin/env python3
"""
VIM Media | Web Audio Sync Service

A web-based tool by VIM Media that:

- Lets users upload multiple camera clips and external audio files
- Supports standard video containers (.mp4, .mov, .mxf, etc.)
- Supports RAW camera formats like Blackmagic RAW (.braw),
  RED (.r3d), and Canon Cinema RAW (.crm)

Per clip (grouped by filename prefix, e.g. A001_cam.mp4 + A001_zoom.wav):

  * Uses onboard/scratch audio from the camera as sync reference
  * Computes offset to each external recorder via waveform correlation
  * Builds a multi-track .mov suitable for Adobe Premiere Pro and Final Cut Pro:

      - NON-RAW footage:
          - Video: copied (no re-encode)
          - Audio tracks:
              Track 1: camera scratch
              Track 2..N: external synced tracks

      - RAW footage (.braw, .r3d, .crm):
          - Video: transcoded to ProRes 422 HQ proxy
          - Audio tracks:
              Track 1: camera scratch
              Track 2..N: external synced tracks

Usage (development):

  pip install flask numpy scipy soundfile
  # Install ffmpeg on the server (must be on PATH)
  python app.py

Then open: http://localhost:5000
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

# Common video container/codecs
VIDEO_EXTS = {
    ".mp4", ".mov", ".mxf", ".avi", ".mkv",
    # RAW camera formats (container or standalone)
    ".braw",  # Blackmagic RAW
    ".r3d",   # RED RAW
    ".crm",   # Canon Cinema RAW
}

# RAW formats that we will proxy to ProRes
RAW_VIDEO_EXTS = {".braw", ".r3d", ".crm"}

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac"}

ANALYSIS_SAMPLE_RATE = 48000  # Standard for video post workflows
DEFAULT_AUDIO_CODEC = "pcm_s16le"  # Uncompressed PCM (great for NLEs)

# Flask app
app = Flask(__name__)

# Allow fairly large uploads (adjust for your server)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024 * 1024  # 8 GB total per request


# ============================================================
# HTML FRONTEND (VIM Media Branding)
# ============================================================

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>VIM Media | Audio Sync Service</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <!-- Tailwind CSS via CDN -->
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
  </style>
</head>
<body class="min-h-screen flex items-center justify-center px-4 py-10">
  <div class="w-full max-w-3xl bg-watchBlack/90 border border-white/10 rounded-3xl shadow-2xl backdrop-blur-md p-6 sm:p-8">
    <!-- Header -->
    <header class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-watchRed flex items-center justify-center">
          <span class="text-white text-lg font-bold tracking-tight">VIM</span>
        </div>
        <div>
          <h1 class="text-xl sm:text-2xl font-semibold tracking-tight">
            Audio Sync Service
          </h1>
          <p class="text-xs sm:text-sm text-slate-300">
            Provided by VIM Media, LLC &mdash; Multi-track, post-ready audio sync for editors.
          </p>
        </div>
      </div>
      <a href="https://watchvim.com" target="_blank"
         class="hidden sm:inline-flex items-center text-xs font-semibold text-watchGold hover:text-white">
        watchvim.com &rsaquo;
      </a>
    </header>

    <!-- Description -->
    <section class="mb-6 text-sm text-slate-200 space-y-2">
      <p>
        Upload your camera clips and external audio files. This service automatically
        synchronizes waveforms and delivers an edit-ready <span class="font-semibold text-watchGold">.mov</span>
        with multiple audio tracks compatible with <span class="font-semibold">Adobe Premiere Pro</span>
        and <span class="font-semibold">Final Cut Pro</span>.
      </p>
      <p class="text-xs text-slate-400">
        Clips are grouped by filename prefix (ex: <code>A001_cam.mp4</code>,
        <code>A001_zoom.wav</code>, <code>A001_boom.wav</code> &rarr;
        <code>A001_synced.mov</code>).
      </p>
      <ul class="text-xs text-slate-300 list-disc pl-4 space-y-1">
        <li>Standard footage (.mp4, .mov, .mxf, etc.) &rarr; video copied (no re-encode) + multi-track audio.</li>
        <li>RAW footage (.braw, .r3d, .crm) &rarr; transcoded to ProRes 422 HQ proxy + multi-track audio.</li>
      </ul>
    </section>

    <!-- Upload Form -->
    <form id="uploadForm" class="space-y-5">
      <div>
        <label class="block text-sm font-medium mb-1">Upload files</label>
        <input id="files" name="files" type="file" multiple
               class="block w-full text-sm text-slate-100
                      file:mr-3 file:py-2 file:px-4
                      file:rounded-md file:border-0
                      file:text-sm file:font-semibold
                      file:bg-watchRed file:text-white
                      hover:file:bg-red-700
                      cursor-pointer" />
        <p class="mt-2 text-xs text-slate-400">
          Include your camera video (.mp4, .mov, .mxf, .braw, .r3d, .crm) and matching external audio (.wav, .mp3, .m4a, etc.).
          Make sure filenames share a prefix for each clip (e.g. <code>SC01_T01_*.ext</code>).
        </p>
      </div>

      <button type="submit"
              class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-full
                     bg-watchGold text-black text-sm font-semibold
                     hover:bg-yellow-400 transition">
        <span>Sync &amp; Download</span>
      </button>
    </form>

    <!-- Status -->
    <div id="status" class="mt-4 text-xs sm:text-sm text-slate-300"></div>

    <!-- Footer -->
    <footer class="mt-6 border-t border-white/10 pt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
      <p class="text-[11px] text-slate-400">
        &copy; <span id="year"></span> VIM Media, LLC. All rights reserved.
      </p>
      <p class="text-[11px] text-slate-500">
        Built for post-production teams who live in timelines, bins, and multitrack madness.
      </p>
    </footer>
  </div>

  <script>
    // Year
    document.getElementById('year').textContent = new Date().getFullYear();

    const form = document.getElementById('uploadForm');
    const statusEl = document.getElementById('status');
    const filesInput = document.getElementById('files');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (!filesInput.files.length) {
        alert('Please select at least one file.');
        return;
      }

      statusEl.textContent = 'Uploading & processing… this may take a while for large files.';

      const formData = new FormData();
      for (const f of filesInput.files) {
        formData.append('files', f);
      }

      try {
        const res = await fetch('/sync', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const text = await res.text();
          statusEl.textContent = 'Error: ' + text;
          return;
        }

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

        statusEl.textContent = 'Done! Your synced file(s) have downloaded.';
      } catch (err) {
        console.error(err);
        statusEl.textContent = 'Unexpected error. Please check the browser console or contact VIM Media support.';
      }
    });
  </script>
</body>
</html>
"""


# ============================================================
# CORE SYNC LOGIC
# ============================================================

def ensure_ffmpeg():
    """Ensure ffmpeg is installed and available."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg on your server and ensure it is on PATH.")


def run_ffmpeg(args):
    """
    Run ffmpeg with -y plus provided args.
    Raises RuntimeError on failure.
    """
    cmd = ["ffmpeg", "-y"] + args
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print("FFmpeg error:", proc.stderr)
        raise RuntimeError("ffmpeg command failed")


def extract_mono_wav(input_path: str, output_path: str, sample_rate: int = ANALYSIS_SAMPLE_RATE):
    """
    Extract or convert any media's audio to mono WAV at given sample rate.
    Used for waveform analysis only (not for final delivery).
    """
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
    Estimate offset between camera audio and external audio via cross-correlation.

    Return:
        offset_seconds (float)
          > 0 : external audio starts that many seconds AFTER camera
          < 0 : external audio starts that many seconds BEFORE camera
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

    offset_seconds > 0  => external starts later than camera
    offset_seconds < 0  => external starts earlier than camera
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
      - Mux final .mov:

        NON-RAW:
          -c:v copy           (video untouched)
          -c:a pcm_s16le      (multi-track audio)

        RAW (.braw, .r3d, .crm):
          -c:v prores_ks      (ProRes 422 HQ proxy)
          -c:a pcm_s16le
    """
    ensure_ffmpeg()

    with tempfile.TemporaryDirectory() as workdir:
        # Extract camera mono WAV for analysis
        cam_wav = os.path.join(workdir, "cam.wav")
        extract_mono_wav(video_path, cam_wav, sample_rate)
        cam_audio, sr_cam = load_audio_mono(cam_wav)

        aligned_paths = []

        for idx, ext_path in enumerate(external_audio_paths):
            ext_wav = os.path.join(workdir, f"ext_{idx}.wav")
            extract_mono_wav(ext_path, ext_wav, sample_rate)
            ext_audio, sr_ext = load_audio_mono(ext_wav)

            if sr_cam != sr_ext:
                raise RuntimeError(f"Sample rate mismatch cam={sr_cam}, ext={sr_ext} after convert")

            offset = estimate_offset_seconds(cam_audio, ext_audio, sr_cam)
            print(f"[Clip] {os.path.basename(video_path)} / "
                  f"{os.path.basename(ext_path)} offset: {offset:.3f} s")

            aligned_ext = build_aligned_external(cam_audio, ext_audio, sr_cam, offset)
            aligned_wav = os.path.join(workdir, f"ext_{idx}_aligned.wav")
            sf.write(aligned_wav, aligned_ext, sr_cam, subtype="PCM_16")
            aligned_paths.append(aligned_wav)

        # Build ffmpeg command
        args = ["-i", video_path]
        for ap in aligned_paths:
            args += ["-i", ap]

        # Map video + all audio streams
        args += [
            "-map", "0:v:0",  # camera video
            "-map", "0:a:0",  # camera scratch audio (if present)
        ]

        for i in range(len(aligned_paths)):
            args += ["-map", f"{i + 1}:a:0"]

        # Decide RAW vs NON-RAW behavior
        ext = os.path.splitext(video_path)[1].lower()
        is_raw = ext in RAW_VIDEO_EXTS

        if is_raw:
            # RAW -> ProRes 422 HQ proxy
            args += [
                "-c:v", "prores_ks",
                "-profile:v", "3",           # 3 = ProRes 422 HQ
                "-pix_fmt", "yuv422p10le",   # standard ProRes pixel format
            ]
        else:
            # Non-RAW -> copy video stream
            args += ["-c:v", "copy"]

        args += [
            "-c:a", DEFAULT_AUDIO_CODEC,  # pcm_s16le
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]

        run_ffmpeg(args)


# ============================================================
# HELPERS
# ============================================================

def classify_and_group_files(temp_dir, uploaded_files):
    """
    Save uploads to temp_dir, classify by extension, then group into clips.

    Clips are grouped by filename prefix before first underscore.
      A001_cam.mp4  -> key A001
      A001_zoom.wav -> key A001

    Returns:
      clips: dict[clip_key] = { "videos": [...], "audios": [...] }
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
        clip_key = base.split("_")[0]  # customize if needed

        clip = clips.setdefault(clip_key, {"videos": [], "audios": []})

        if ext in VIDEO_EXTS:
            clip["videos"].append(dest_path)
        elif ext in AUDIO_EXTS:
            clip["audios"].append(dest_path)
        else:
            # Unknown file type -> ignore
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
                # Need at least one video and one external audio per clip
                continue

            video_path = videos[0]  # use first video as reference
            ext_paths = audios

            out_name = f"{clip_key}_synced.mov"
            out_path = os.path.join(tmpdir, out_name)

            process_clip_to_multitrack_mov(video_path, ext_paths, out_path)
            outputs.append(out_path)

        if not outputs:
            return (
                "No valid clip groups found. "
                "Make sure each clip has at least one video file and one audio file, "
                "with matching filename prefixes (e.g. SC01_T01_cam.mp4 & SC01_T01_zoom.wav).",
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
        # For production you may want a background cleanup job for tmp dirs.
        # Here we leave tmpdir for OS/user to clean if needed.
        pass


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    # For production:
    #   - Run behind a WSGI server like gunicorn or uWSGI
    #   - Example: gunicorn -w 4 -b 0.0.0.0:8000 app:app
    #
    # Dev / local:
    #   python app.py
    #   Visit http://localhost:5000
    app.run(host="0.0.0.0", port=5000, debug=True)
