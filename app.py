#!/usr/bin/env python3
"""
VIM Media | Audio Sync Service (AudioSync v1)

Features:
- Upload multiple camera clips + external audio (typically zipped as one job)
- Support standard formats (mp4, mov, mxf, wav, mp3, aiff, etc.)
- Waveform-based sync step placeholder (hook in your real sync logic)
- Multi-track .mov/.mp4 output for NLEs (Adobe Premiere Pro, FCP, etc.)
- Pay-per-job checkout + subscription tiers via PayPal
- Optional user accounts with profile page and sync history
- Streaming preview player so users can review synced result before paying
- Download locked until job is marked as paid.

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
    jsonify,
    render_template,
)

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# ============================================================
# CONFIGURATION
# ============================================================

# 👇 Set this to your real backend URL (DigitalOcean / domain)
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.audiosync.watchvim.com")

# Storage
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER", os.path.join(BASE_DIR, "outputs"))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "audiosync.db"))

# Make sure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# File limits / allowed
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB
ALLOWED_EXTENSIONS = {
    "mp4",
    "mov",
    "mxf",
    "wav",
    "mp3",
    "aiff",
    "aif",
    "m4a",
    "zip",
}

# PayPal configuration (provided by you)
PAYPAL_CLIENT_ID = os.getenv(
    "PAYPAL_CLIENT_ID",
    "AQC5qjaOAHkOLQvTh8fKm_zeV0Wfv9_pUvxk8DQQqUgu6E_KhQVpnJxMKC7MxzM_2PpA3jYpExdJXin5",
)

PAYPAL_PLANS = {
    "indie": os.getenv("PAYPAL_PLAN_INDIE", "P-5HF24724VN545651WNEZ6SDQ"),
    "studio": os.getenv("PAYPAL_PLAN_STUDIO", "P-7W490604V8434754DNEZ6TAA"),
    "pro_studio": os.getenv("PAYPAL_PLAN_PRO", "P-4KL402168F127405GNEZ6TWY"),
}

# Flask app
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = os.getenv("SECRET_KEY", "vim-audiosync-dev-secret")


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            email TEXT,
            original_filename TEXT,
            original_path TEXT NOT NULL,
            output_path TEXT,
            status TEXT NOT NULL DEFAULT 'processing', -- processing, ready, error
            plan TEXT,     -- indie / studio / pro_studio
            price_cents INTEGER,
            is_paid INTEGER NOT NULL DEFAULT 0,
            notes TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# SIMPLE SYNC PIPELINE PLACEHOLDER
# ============================================================

def run_sync_pipeline(job_id: int, input_path: str) -> str:
    """
    Placeholder for real audio/video sync logic.

    For now, we:
    - If it's a .zip, extract it to a temp dir and just pick one video file.
    - Copy (or re-encode) the main video to OUTPUT_FOLDER as the "synced" file.

    Replace this with your actual sync engine (FFmpeg, Resolve, custom binary, etc).
    """
    job_output_dir = os.path.join(OUTPUT_FOLDER, f"job_{job_id}")
    os.makedirs(job_output_dir, exist_ok=True)

    # Determine main input
    main_video = None
    work_dir = tempfile.mkdtemp(prefix=f"audiosync_job_{job_id}_")

    try:
        if input_path.lower().endswith(".zip"):
            with zipfile.ZipFile(input_path, "r") as zf:
                zf.extractall(work_dir)
            # Find first video-like file
            for root, _, files in os.walk(work_dir):
                for f in files:
                    if f.lower().split(".")[-1] in ("mp4", "mov", "mxf"):
                        main_video = os.path.join(root, f)
                        break
                if main_video:
                    break
        else:
            main_video = input_path

        if not main_video or not os.path.exists(main_video):
            raise RuntimeError("No valid video file found for sync.")

        # In real implementation, call your sync engine here:
        # e.g., subprocess.run([...])
        # For now, we just copy the file as a placeholder "synced" output.
        output_path = os.path.join(job_output_dir, "synced_preview.mp4")
        shutil.copy2(main_video, output_path)

        return output_path

    finally:
        # Clean up temporary working directory (keep job_output_dir)
        if os.path.isdir(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)


def update_job_status(job_id: int, status: str, output_path: str | None = None, notes: str | None = None):
    conn = get_db()
    if output_path is not None and notes is not None:
        conn.execute(
            "UPDATE jobs SET status = ?, output_path = ?, notes = ? WHERE id = ?",
            (status, output_path, notes, job_id),
        )
    elif output_path is not None:
        conn.execute(
            "UPDATE jobs SET status = ?, output_path = ? WHERE id = ?",
            (status, output_path, job_id),
        )
    elif notes is not None:
        conn.execute(
            "UPDATE jobs SET status = ?, notes = ? WHERE id = ?",
            (status, notes, job_id),
        )
    else:
        conn.execute(
            "UPDATE jobs SET status = ? WHERE id = ?",
            (status, job_id),
        )
    conn.commit()
    conn.close()


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    """
    Simple landing endpoint for health check.
    Frontend can also use BACKEND_URL + /config to bootstrap.
    """
    return jsonify(
        {
            "service": "VIM AudioSync",
            "status": "ok",
            "backend_url": BACKEND_URL,
        }
    )


@app.route("/config", methods=["GET"])
def public_config():
    """
    Public config endpoint for frontend apps (web, React, etc).
    DO NOT expose secrets here (client ID is public in PayPal JS SDK).
    """
    return jsonify(
        {
            "backendUrl": BACKEND_URL,
            "paypalClientId": PAYPAL_CLIENT_ID,
            "paypalPlans": PAYPAL_PLANS,
        }
    )


@app.route("/upload", methods=["POST"])
def upload():
    """
    Upload route for a new sync job.

    Expected form fields:
    - email (optional)
    - plan (indie | studio | pro_studio) - optional
    - file (File)  <-- can be .zip or a direct media file
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request. Use field name 'file'."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed."}), 400

    email = request.form.get("email")
    plan = request.form.get("plan")  # "indie", "studio", "pro_studio"
    orig_filename = secure_filename(file.filename)

    # Persist input
    created_at = datetime.utcnow().isoformat() + "Z"
    original_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{created_at}_{orig_filename}")
    file.save(original_path)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO jobs (created_at, email, original_filename, original_path, status, plan)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (created_at, email, orig_filename, original_path, "processing", plan),
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Run sync pipeline (synchronously for now; swap for Celery or RQ in production)
    try:
        output_path = run_sync_pipeline(job_id, original_path)
        update_job_status(job_id, "ready", output_path=output_path, notes="Sync completed.")
    except Exception as exc:  # noqa: BLE001
        update_job_status(job_id, "error", notes=str(exc))
        return jsonify({"jobId": job_id, "status": "error", "error": str(exc)}), 500

    return jsonify(
        {
            "jobId": job_id,
            "status": "ready",
            "previewUrl": f"{BACKEND_URL}/preview/{job_id}",
        }
    )


@app.route("/job/<int:job_id>", methods=["GET"])
def job_status(job_id: int):
    """
    Fetch status for a given job.
    Frontend can poll this to know when the sync is ready.
    """
    conn = get_db()
    job = conn.execute(
        "SELECT id, created_at, email, original_filename, status, plan, is_paid FROM jobs WHERE id = ?",
        (job_id,),
    ).fetchone()
    conn.close()

    if job is None:
        return jsonify({"error": "Job not found."}), 404

    return jsonify(
        {
            "id": job["id"],
            "createdAt": job["created_at"],
            "email": job["email"],
            "originalFilename": job["original_filename"],
            "status": job["status"],
            "plan": job["plan"],
            "isPaid": bool(job["is_paid"]),
            "previewUrl": f"{BACKEND_URL}/preview/{job_id}" if job["status"] == "ready" else None,
            "downloadUrl": f"{BACKEND_URL}/download/{job_id}" if job["is_paid"] else None,
        }
    )


# ============================================================
# PREVIEW + DOWNLOAD
# ============================================================

@app.route("/preview/<int:job_id>")
def preview(job_id: int):
    """
    Render a preview page for a given job.
    User can stream the synced video/audio but cannot download it.
    """
    conn = get_db()
    job = conn.execute(
        "SELECT id, output_path, is_paid, status FROM jobs WHERE id = ?",
        (job_id,),
    ).fetchone()
    conn.close()

    if job is None:
        return "Job not found", 404

    if job["status"] != "ready" or not job["output_path"]:
        return "This job is not ready for preview yet.", 400

    return render_template(
        "preview.html",
        job_id=job["id"],
        is_paid=bool(job["is_paid"]),
    )


@app.route("/preview/media/<int:job_id>")
def preview_media(job_id: int):
    """
    Stream the synced video/audio for preview (no direct download).
    """
    conn = get_db()
    job = conn.execute(
        "SELECT id, output_path, status FROM jobs WHERE id = ?",
        (job_id,),
    ).fetchone()
    conn.close()

    if job is None:
        return "Job not found", 404

    if job["status"] != "ready" or not job["output_path"]:
        return "This job is not ready for preview yet.", 400

    output_path = job["output_path"]
    if not os.path.exists(output_path):
        return "Synced file not found on server.", 404

    # No as_attachment → browser plays it inline
    return send_file(
        output_path,
        mimetype="video/mp4",
        as_attachment=False,
        download_name=f"audiosync-job-{job_id}-preview.mp4",
    )


@app.route("/download/<int:job_id>")
def download(job_id: int):
    """
    Allow download ONLY if the job has been paid for.
    """
    conn = get_db()
    job = conn.execute(
        "SELECT id, output_path, is_paid, status FROM jobs WHERE id = ?",
        (job_id,),
    ).fetchone()
    conn.close()

    if job is None:
        return "Job not found", 404

    if not job["is_paid"]:
        return "Payment required before download.", 403

    if job["status"] != "ready":
        return "This job is not ready for download yet.", 400

    output_path = job["output_path"]
    if not output_path or not os.path.exists(output_path):
        return "File not found on server.", 404

    return send_file(
        output_path,
        mimetype="video/mp4",
        as_attachment=True,
        download_name=f"VIM-AudioSync-job-{job_id}.mp4",
    )


# ============================================================
# PAYPAL HOOKS (SIMPLE)
# ============================================================

@app.route("/paypal/mark-paid/<int:job_id>", methods=["POST"])
def mark_paid(job_id: int):
    """
    SIMPLE INTERNAL ENDPOINT:
    - You can call this from a PayPal webhook handler or admin UI
      once payment/subscription is confirmed.
    - In production, protect this route (API key, auth, IP allowlist, etc.)
    """
    conn = get_db()
    job = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job is None:
        conn.close()
        return jsonify({"error": "Job not found"}), 404

    conn.execute("UPDATE jobs SET is_paid = 1 WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

    return jsonify({"jobId": job_id, "isPaid": True})


@app.route("/paypal/webhook", methods=["POST"])
def paypal_webhook():
    """
    Minimal placeholder webhook endpoint.

    In a real integration you would:
    - Verify the webhook with PayPal (transmission id, signature, etc.).
    - Inspect the event type and resource.
    - Extract your own custom_id / metadata that contains job_id.
    - Mark corresponding job as paid.

    Here we just parse JSON and look for resource.custom_id as job_id.
    """
    event = request.get_json(silent=True) or {}
    resource = event.get("resource", {})
    custom_id = resource.get("custom_id")

    if not custom_id:
        # Not a job-linked event; ignore gracefully
        return jsonify({"status": "ignored", "reason": "no custom_id"}), 200

    try:
        job_id = int(custom_id)
    except (TypeError, ValueError):
        return jsonify({"status": "ignored", "reason": "invalid custom_id"}), 200

    conn = get_db()
    job = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if job is None:
        conn.close()
        return jsonify({"status": "ignored", "reason": "job not found"}), 200

    conn.execute("UPDATE jobs SET is_paid = 1 WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "jobId": job_id})


# ============================================================
# APP STARTUP
# ============================================================

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
