// popup.js

const OPEN_PATTERNS = [
  /why\s+(do\s+you\s+want|are\s+you\s+interested|us|this)/i,
  /tell\s+us/i,
  /describe\s+(your|a\s+time|how)/i,
  /what\s+(do\s+you|makes\s+you|sets\s+you|is\s+your)/i,
  /how\s+(have\s+you|would\s+you|do\s+you)/i,
  /share\s+(a\s+time|an\s+example|your)/i,
  /cover\s+letter/i,
  /motivation/i,
  /additional\s+information/i,
  /anything\s+else/i,
];

function isOpen(field) {
  return field.type === 'textarea' &&
    OPEN_PATTERNS.some(p => p.test(field.label));
}

function classifyFields(fields) {
  const standard = [], open = [];
  for (const f of fields) {
    (isOpen(f) ? open : standard).push(f);
  }
  return { standard, open };
}

// ── UI helpers ─────────────────────────────────────────────────────────────

function setResult(msg, type = 'success') {
  const el = document.getElementById('result');
  el.textContent = msg;
  el.className = type;
}

function clearResult() {
  const el = document.getElementById('result');
  el.className = 'hidden';
  el.textContent = '';
}

// ── Main ───────────────────────────────────────────────────────────────────

let pageInfo   = null;   // { platform, url, title, fields }
let classified = null;   // { standard, open }
let profile    = null;
let corpus     = [];
let apiKey     = '';
let model      = 'gemini-2.0-flash';
let wordLimit  = 150;

async function init() {
  // Load stored settings
  const stored = await chrome.storage.local.get([
    'profile', 'corpus', 'apiKey', 'model', 'wordLimit',
  ]);
  profile   = stored.profile   ?? null;
  corpus    = stored.corpus    ?? [];
  apiKey    = stored.apiKey    ?? '';
  model     = stored.model     ?? 'gemini-2.0-flash';
  wordLimit = stored.wordLimit ?? 150;

  // Update profile row
  const nameEl   = document.getElementById('profile-name');
  const warnEl   = document.getElementById('no-profile-warning');
  if (profile?.first_name) {
    nameEl.textContent = `${profile.first_name} ${profile.last_name ?? ''}`.trim();
    warnEl.classList.add('hidden');
  } else {
    nameEl.textContent = 'No profile loaded';
    warnEl.classList.remove('hidden');
  }

  // Query the active tab and send DETECT message
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  try {
    pageInfo = await chrome.tabs.sendMessage(tab.id, { type: 'DETECT' });
  } catch {
    setResult('Content script not ready. Reload the page and try again.', 'error');
    return;
  }

  // Platform badge
  const badge = document.getElementById('platform-badge');
  badge.textContent = pageInfo.platform;
  badge.className   = `badge ${pageInfo.platform}`;

  // Job title
  const titleEl = document.getElementById('job-title');
  titleEl.textContent = tab.title?.replace(/\s*[-|].*$/, '').trim() ?? '';

  // Classify fields
  classified = classifyFields(pageInfo.fields);
  const countsEl = document.getElementById('field-counts');
  countsEl.textContent =
    `${classified.standard.length} standard · ${classified.open.length} open`;

  // Enable buttons
  if (classified.standard.length > 0 && profile) {
    document.getElementById('btn-fill-standard').disabled = false;
  }
  if (classified.open.length > 0 && profile && apiKey) {
    document.getElementById('btn-generate').disabled = false;
  }
}

// ── Button: Fill Standard ──────────────────────────────────────────────────

document.getElementById('btn-fill-standard').addEventListener('click', async () => {
  clearResult();
  setResult('Filling…', 'loading');

  // Build answers map from profile
  const PROFILE_MAP = {
    first_name:   ['first name', 'given name'],
    last_name:    ['last name', 'family name', 'surname'],
    full_name:    ['full name', 'your name', 'name'],
    email:        ['email', 'e-mail'],
    phone:        ['phone', 'mobile', 'telephone'],
    linkedin:     ['linkedin'],
    github:       ['github'],
    website:      ['website', 'portfolio'],
    location:     ['city', 'location', 'address'],
    work_auth:    ['authorized to work', 'work authorization', 'visa status'],
    sponsorship:  ['require sponsorship', 'visa sponsorship'],
    salary:       ['salary', 'compensation'],
    start_date:   ['start date', 'available to start'],
    years_exp:    ['years of experience'],
    gender:       ['gender'],
    ethnicity:    ['ethnicity', 'race'],
    veteran:      ['veteran'],
    disability:   ['disability'],
  };

  const answers = {};
  for (const field of classified.standard) {
    const labelLower = field.label.toLowerCase();
    for (const [key, patterns] of Object.entries(PROFILE_MAP)) {
      if (patterns.some(p => labelLower.includes(p)) && profile[key]) {
        answers[field.id]    = String(profile[key]);
        answers[field.label] = String(profile[key]);
        break;
      }
    }
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const resp  = await chrome.tabs.sendMessage(tab.id, { type: 'FILL', answers });
  setResult(`Filled ${resp.filled} field${resp.filled !== 1 ? 's' : ''}.`, 'success');
});

// ── Button: Generate AI Answers ────────────────────────────────────────────

document.getElementById('btn-generate').addEventListener('click', async () => {
  clearResult();

  const btn = document.getElementById('btn-generate');
  btn.disabled = true;
  setResult(`Calling Gemini for ${classified.open.length} question(s)…`, 'loading');

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  // Get job description text from the page if available
  const jdText = pageInfo.jdText ?? '';

  const resp = await chrome.runtime.sendMessage({
    type:       'GENERATE_ANSWERS',
    openFields: classified.open,
    profile,
    corpus,
    jdText,
    apiKey,
    model,
    wordLimit,
  });

  if (!resp.success) {
    setResult(`Error: ${resp.error}`, 'error');
    btn.disabled = false;
    return;
  }

  const fillResp = await chrome.tabs.sendMessage(tab.id, {
    type:    'FILL',
    answers: resp.answers,
  });

  setResult(
    `AI answers filled for ${fillResp.filled} field${fillResp.filled !== 1 ? 's' : ''}. Review before submitting.`,
    'success',
  );
  btn.disabled = false;
});

// ── Settings links ─────────────────────────────────────────────────────────

function openSettings() {
  chrome.runtime.openOptionsPage();
}
document.getElementById('settings-link').addEventListener('click', e => {
  e.preventDefault(); openSettings();
});
document.getElementById('open-settings')?.addEventListener('click', e => {
  e.preventDefault(); openSettings();
});

// ── Boot ───────────────────────────────────────────────────────────────────

init();
