// background.js — service worker; handles Gemini API calls

const SYSTEM_PROMPT = `You are writing job application answers on behalf of the applicant.
Your output will be read by humans, so it must sound like a real person wrote it.

HARD RULES — violating any of these is a failure:
- No em dashes (—). Use a comma, period, or rewrite the clause instead.
- No semicolons in casual prose. Use two sentences.
- No filler openers: "In today's world", "I am excited to", "I am passionate about", "It is worth noting"
- No buzzwords: leverage, synergy, robust, cutting-edge, seamlessly, delve, spearhead, cultivate, foster, paradigm, holistic, dynamic, transformative, impactful
- No vague superlatives: "extremely", "highly motivated", "results-driven", "detail-oriented"
- Don't start consecutive sentences with "I". Vary the sentence subject.

STYLE GUIDE:
- First person, conversational but professional
- Use contractions naturally (I've, we've, it's, I'm)
- Mix sentence lengths: punchy short sentences next to longer ones
- Lead with a specific detail, number, or example — not a thesis statement
- Under the word limit. Concise beats comprehensive.

Output only the answer text — no labels, no headers, no meta-commentary.`;


function buildPrompt(field, profile, corpus, jdText, wordLimit) {
  const lines = [
    `QUESTION: ${field.label}`,
    `WORD LIMIT: ${wordLimit}`,
    '',
    'APPLICANT PROFILE:',
    profileToText(profile),
  ];

  if (corpus?.length) {
    lines.push('', 'EXPERIENCE STORIES (use these when relevant):');
    corpus.slice(0, 5).forEach(s => lines.push(`- ${s}`));
  }

  if (jdText) {
    lines.push('', 'JOB CONTEXT:');
    lines.push(jdText.slice(0, 1200));
  }

  return lines.join('\n');
}

function profileToText(profile, indent = 0) {
  return Object.entries(profile)
    .map(([k, v]) => {
      const pad = '  '.repeat(indent);
      if (typeof v === 'object' && !Array.isArray(v))
        return `${pad}${k}:\n${profileToText(v, indent + 1)}`;
      if (Array.isArray(v))
        return `${pad}${k}: ${v.join(', ')}`;
      return `${pad}${k}: ${v}`;
    })
    .join('\n');
}

async function callGemini(prompt, apiKey, model) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
  const body = {
    system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { maxOutputTokens: 600, temperature: 0.7 },
  };

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Gemini API error ${res.status}`);
  }

  const data = await res.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? '';
}


chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== 'GENERATE_ANSWERS') return;

  const { openFields, profile, corpus, jdText, apiKey, model, wordLimit } = msg;

  (async () => {
    const answers = {};
    try {
      for (const field of openFields) {
        const prompt = buildPrompt(field, profile, corpus, jdText, wordLimit);
        answers[field.id] = await callGemini(prompt, apiKey, model);
        // Also index by label so content.js can match either way
        answers[field.label] = answers[field.id];
      }
      sendResponse({ success: true, answers });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  })();

  return true; // keep message channel open for async
});
