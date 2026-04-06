// Claude Synthesizer v2 -- Content script
// Thin glue: message listeners and DOM interactions only.
// Depends on window.RecurateExtractor (extractor.js), window.SynthPrompts (prompts.js),
// window.SynthAPI (claude-api.js), and window.SynthOrchestrator (orchestrator.js).
(function () {
  'use strict';

  // --- Message listener ---

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {

    // v2 pipeline: receives chat data + options from background.js
    if (message.action === 'RUN_V2_PIPELINE') {
      sendResponse({ started: true });
      window.SynthOrchestrator.run(message.chatData, message.options)
        .then(result =>
          chrome.runtime.sendMessage({ action: 'SYNTHESIS_COMPLETE', result })
        )
        .catch(e =>
          chrome.runtime.sendMessage({
            action: 'SYNTHESIS_COMPLETE',
            result: { success: false, error: e.message },
          })
        );
      return false;
    }

    if (message.action === 'LIST_PROJECTS') {
      window.SynthAPI.getOrgId()
        .then(orgId => window.SynthAPI.listProjects(orgId))
        .then(projects => sendResponse({ projects }))
        .catch(() => sendResponse({ projects: [] }));
      return true;
    }

    // --- Extraction (called by background.js for DOM scraping) ---

    if (message.action === 'WAIT_FOR_MESSAGES') {
      const POLL_MS = 500;
      const TIMEOUT_MS = 30_000;
      const start = Date.now();
      (function poll() {
        const count = document.querySelectorAll(
          '[data-testid="user-message"], [data-is-streaming="false"]'
        ).length;
        if (count > 0) {
          sendResponse({ ready: true, count });
        } else if (Date.now() - start > TIMEOUT_MS) {
          sendResponse({ ready: false, count: 0 });
        } else {
          setTimeout(poll, POLL_MS);
        }
      })();
      return true;
    }

    if (message.action === 'EXTRACT_CHAT') {
      const E = window.RecurateExtractor;
      E.extractConversation()
        .then(messages => {
          const title = E.getConversationTitle() || 'Untitled';
          sendResponse({ messages, title });
        })
        .catch(e => sendResponse({ error: e.message }));
      return true;
    }

    if (message.action === 'GET_PROJECT_CONVERSATIONS') {
      (async () => {
        try {
          const orgId = await window.SynthAPI.getOrgId();
          const storage = await chrome.storage.local.get(['synth_project_id']);
          const convos = await window.SynthAPI.listProjectConversations(
            orgId, storage.synth_project_id
          );
          sendResponse({ conversations: convos });
        } catch {
          sendResponse({ conversations: [] });
        }
      })();
      return true;
    }

    if (message.action === 'DOWNLOAD_TEXT') {
      const blob = new Blob([message.content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = message.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      sendResponse({ success: true });
      return false;
    }

    return false;
  });

  // --- Message count warning ---

  const WARNING_THRESHOLD = 400;
  const CHECK_INTERVAL_MS = 30_000;
  let lastWarningBucket = 0;

  function checkMessageCount() {
    const count = document.querySelectorAll(
      '[data-testid="user-message"], [data-is-streaming="false"]'
    ).length;
    const bucket = Math.floor(count / 100) * 100;
    if (bucket >= WARNING_THRESHOLD && bucket > lastWarningBucket) {
      lastWarningBucket = bucket;
      showWarning(count);
    }
  }

  function showWarning(count) {
    const existing = document.getElementById('synth-warning');
    if (existing) existing.remove();

    const banner = document.createElement('div');
    banner.id = 'synth-warning';
    Object.assign(banner.style, {
      position: 'fixed', top: '8px', left: '50%', transform: 'translateX(-50%)',
      zIndex: '2147483647', padding: '10px 16px', borderRadius: '10px',
      background: '#fef3c7', color: '#92400e', fontSize: '13px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)', display: 'flex',
      alignItems: 'center', gap: '10px', border: '1px solid #fcd34d',
    });
    banner.innerHTML = `
      <span style="font-size:16px;">&#x26A0;</span>
      <span>This conversation has <strong>${count}+ messages</strong>. Consider starting a new chat.</span>
      <button id="synth-warning-dismiss" style="border:none;background:transparent;color:#92400e;font-size:16px;cursor:pointer;padding:0 4px;margin-left:8px;">&times;</button>
    `;
    document.body.appendChild(banner);
    document.getElementById('synth-warning-dismiss')
      .addEventListener('click', () => banner.remove());
    setTimeout(() => banner.parentElement && banner.remove(), 15_000);
  }

  setInterval(checkMessageCount, CHECK_INTERVAL_MS);
  setTimeout(checkMessageCount, 5_000);
})();
