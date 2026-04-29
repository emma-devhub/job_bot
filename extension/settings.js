// settings.js

const PROFILE_FIELDS = [
  'first_name', 'last_name', 'email', 'phone',
  'linkedin', 'github', 'website', 'location',
  'work_auth', 'sponsorship', 'salary', 'start_date', 'years_exp',
];

async function load() {
  const stored = await chrome.storage.local.get([
    'profile', 'corpus', 'apiKey', 'model', 'wordLimit', 'resumeText',
  ]);

  document.getElementById('api-key').value   = stored.apiKey   ?? '';
  document.getElementById('model').value     = stored.model    ?? 'gemini-2.0-flash';
  document.getElementById('word-limit').value = stored.wordLimit ?? 150;
  document.getElementById('resume_text').value = stored.resumeText ?? '';
  document.getElementById('corpus').value =
    (stored.corpus ?? []).join('\n\n');

  const profile = stored.profile ?? {};
  for (const key of PROFILE_FIELDS) {
    const el = document.getElementById(key);
    if (el) el.value = profile[key] ?? '';
  }
}

async function save() {
  const profile = {};
  for (const key of PROFILE_FIELDS) {
    const val = document.getElementById(key)?.value.trim();
    if (val) profile[key] = val;
  }

  // full_name convenience
  if (profile.first_name && profile.last_name) {
    profile.full_name = `${profile.first_name} ${profile.last_name}`;
  }

  const corpusRaw = document.getElementById('corpus').value.trim();
  const corpus = corpusRaw
    ? corpusRaw.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean)
    : [];

  await chrome.storage.local.set({
    profile,
    corpus,
    resumeText: document.getElementById('resume_text').value.trim(),
    apiKey:     document.getElementById('api-key').value.trim(),
    model:      document.getElementById('model').value,
    wordLimit:  parseInt(document.getElementById('word-limit').value, 10),
  });

  const msg = document.getElementById('saved-msg');
  msg.classList.remove('hidden');
  setTimeout(() => msg.classList.add('hidden'), 2000);
}

document.getElementById('btn-save').addEventListener('click', save);

load();
