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

  <!-- PayPal SDK: client ID injected by Flask -->
  <script src="https://www.paypal.com/sdk/js?client-id={{ paypal_client_id }}&vault=true&intent=subscription&currency=USD"></script>
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
          <span id="userStatus" class="text-slate-300">
            Optional: log in on AudioSync to see your history.
          </span>
          <a id="profileLink"
             class="hidden text-watchGold hover:text-white font-semibold">Profile</a>
          <a id="loginLink"
             class="text-slate-300 hover:text-watchGold font-semibold">Login</a>
          <a id="signupLink"
             class="text-slate-300 hover:text-watchGold font-semibold">Sign up</a>
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
            Upload & preview first. When you are happy with the result, complete payment to unlock download.
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

  <!-- === MAIN SCRIPT (all same-origin calls) === -->
  <script>
    // ===== Payment + PayPal config =====
    const PAYMENT_REQUIRED = true;      // require PayPal before download
    const PAY_PER_JOB_AMOUNT = "7.00";

    // Plan IDs from backend (PAYPAL_PLANS in app.py)
    const INDIE_PLAN_ID  = "{{ paypal_plans.indie }}";
    const STUDIO_PLAN_ID = "{{ paypal_plans.studio }}";
    const PRO_PLAN_ID    = "{{ paypal_plans.pro_studio }}";

    document.getElementById('year').textContent = new Date().getFullYear();

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

    let overlayTimer = null;
    let isProcessing = false;
    let hasPaid = !PAYMENT_REQUIRED;   // set to true if you want to test without PayPal
    let currentJobId = null;
    let currentJobStatus = null;

    // All routes are on the SAME origin now (no BACKEND_BASE_URL needed)
    loginLink.href  = "/login";
    signupLink.href = "/signup";
    profileLink.href = "/profile";

    paymentStatusEl.textContent = PAYMENT_REQUIRED
      ? 'Upload & preview first. When you are happy with the result, complete payment to unlock download.'
      : 'Payment is disabled in this environment (testing mode).';

    syncButton.disabled = false;

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

    // ===== Pay-per-job with PayPal =====
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
            paymentStatusEl.textContent = 'Payment received. You can now download the synced file for this job.';

            if (currentJobId) {
              fetch(`/paypal/mark-paid/${currentJobId}`, {
                method: 'POST'
              })
                .then(r => r.json())
                .then(markRes => {
                  console.log('Marked job as paid:', markRes);
                })
                .catch(err => {
                  console.error('Error marking job as paid:', err);
                });
            } else {
              paymentStatusEl.textContent += ' (Upload your media to create a job.)';
            }
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

    // ===== Subscription buttons (Indie / Studio / Pro) =====
    if (window.paypal) {
      if (INDIE_PLAN_ID) {
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

      if (STUDIO_PLAN_ID) {
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

      if (PRO_PLAN_ID) {
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

    async function pollJobStatus(jobId) {
      try {
        const res = await fetch(`/job/${jobId}`);
        if (!res.ok) {
          console.error('Job status error', res.status);
          return;
        }
        const data = await res.json();
        currentJobStatus = data.status;

        if (data.status === 'ready') {
          hideOverlay();
          const previewLink = data.previewUrl
            ? `<a href="${data.previewUrl}" target="_blank" class="underline text-watchGold">Open preview</a>`
            : '';
          const downloadHint = PAYMENT_REQUIRED
            ? 'Complete payment, then click “Download synced file”.'
            : 'You can now download the synced file.';

          statusEl.innerHTML = `
            Job #${data.id} is <span class="text-watchGold font-semibold">ready</span>.<br/>
            ${previewLink}<br/>
            <button id="downloadButton"
              class="mt-2 inline-flex items-center justify-center gap-2 px-3 py-1.5 rounded-full
              bg-watchGold text-black text-xs font-semibold hover:bg-yellow-400">
              Download synced file
            </button>
            <p class="text-[11px] text-slate-400 mt-1">${downloadHint}</p>
          `;

          const downloadBtn = document.getElementById('downloadButton');
          if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
              if (PAYMENT_REQUIRED && !hasPaid) {
                alert('Please complete payment before downloading. You can preview the result above.');
                return;
              }
              window.location.href = `/download/${jobId}`;
            });
          }
        } else if (data.status === 'error') {
          hideOverlay();
          statusEl.textContent = 'There was an error processing your job. Please contact VIM Media support.';
        } else {
          // still processing
          setTimeout(() => pollJobStatus(jobId), 5000);
        }
      } catch (err) {
        console.error('Error polling job:', err);
      }
    }

    // ===== Upload & sync handler =====
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (!filesInput.files.length) {
        alert('Please select a file to upload (a .zip with your media is recommended).');
        return;
      }

      const file = filesInput.files[0];

      statusEl.textContent = 'Uploading your media and starting the sync… Please keep this tab open.';
      showOverlay();

      const formData = new FormData();
      // Backend expects SINGLE field named "file"
      formData.append('file', file);

      try {
        const res = await fetch('/upload', {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          hideOverlay();
          const text = await res.text();
          statusEl.textContent = 'Error: ' + text;
          return;
        }

        const data = await res.json();
        currentJobId = data.jobId;
        currentJobStatus = data.status;

        statusEl.textContent = `Job #${currentJobId} created. Syncing… This may take a few minutes for large or RAW footage.`;

        // Start polling status until ready
        pollJobStatus(currentJobId);
      } catch (err) {
        console.error(err);
        hideOverlay();
        statusEl.textContent = 'Unexpected error. Please try again or contact VIM Media support.';
      }
    });
  </script>
</body>
</html>
