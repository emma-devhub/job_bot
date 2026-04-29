// content.js — runs on the job application page

// ── Platform detection ─────────────────────────────────────────────────────

function detectPlatform() {
  const url = window.location.href;
  if (/greenhouse\.io/.test(url))       return 'greenhouse';
  if (/ashbyhq\.com|ashby\.com/.test(url)) return 'ashby';
  if (/myworkdayjobs\.com/.test(url))   return 'workday';
  if (/gem\.com/.test(url))             return 'gem';
  return 'unknown';
}

// ── Field discovery ────────────────────────────────────────────────────────

function findInputForLabel(label) {
  // 1. via for= attribute
  const forId = label.getAttribute('for');
  if (forId) {
    const el = document.getElementById(forId);
    if (el) return el;
  }
  // 2. input nested inside label
  const nested = label.querySelector('input, textarea, select');
  if (nested) return nested;

  // 3. next sibling scan
  let sib = label.nextElementSibling;
  for (let i = 0; i < 5 && sib; i++) {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(sib.tagName)) return sib;
    const inner = sib.querySelector('input, textarea, select');
    if (inner) return inner;
    sib = sib.nextElementSibling;
  }
  return null;
}

function discoverFields() {
  const seen = new Set();
  const fields = [];

  for (const label of document.querySelectorAll('label')) {
    const labelText = label.innerText.trim().replace(/\s+/g, ' ');
    if (!labelText) continue;

    const input = findInputForLabel(label);
    if (!input || seen.has(input)) continue;
    seen.add(input);

    const tag = input.tagName.toLowerCase();
    const type = tag === 'select'   ? 'select'
               : tag === 'textarea' ? 'textarea'
               : (input.getAttribute('type') || 'text');

    const id = input.id || input.name
      || labelText.toLowerCase().replace(/[^a-z0-9]+/g, '_');

    fields.push({ id, label: labelText, type, required: !!input.required });
  }

  return fields;
}

// ── Field filling ──────────────────────────────────────────────────────────

// React/Vue track internal state via native setters — bypass them.
function setNativeValue(el, value) {
  const proto = el.tagName === 'TEXTAREA'
    ? window.HTMLTextAreaElement.prototype
    : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  if (setter) setter.call(el, value);
  else el.value = value;
}

function fillInput(el, value) {
  if (!el || value === undefined || value === null) return false;

  if (el.tagName === 'SELECT') {
    const val = String(value).toLowerCase();
    for (const opt of el.options) {
      if (
        opt.value.toLowerCase() === val ||
        opt.text.toLowerCase().includes(val)
      ) {
        opt.selected = true;
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
      }
    }
    return false;
  }

  setNativeValue(el, value);
  el.dispatchEvent(new Event('input',  { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur',   { bubbles: true }));
  return true;
}

function fillFields(answers) {
  const seen = new Set();
  let filled = 0;

  for (const label of document.querySelectorAll('label')) {
    const labelText = label.innerText.trim().replace(/\s+/g, ' ');
    const input = findInputForLabel(label);
    if (!input || seen.has(input)) continue;
    seen.add(input);

    const id = input.id || input.name
      || labelText.toLowerCase().replace(/[^a-z0-9]+/g, '_');

    // Try matching by id first, then by label text
    const value = answers[id] ?? answers[labelText];
    if (value && fillInput(input, value)) filled++;
  }

  return filled;
}

// ── Message listener ───────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  switch (msg.type) {
    case 'DETECT':
      sendResponse({
        platform: detectPlatform(),
        url:      window.location.href,
        title:    document.title,
        fields:   discoverFields(),
      });
      break;

    case 'FILL':
      sendResponse({ filled: fillFields(msg.answers) });
      break;

    default:
      sendResponse({ error: 'unknown message type' });
  }
  return true;
});
