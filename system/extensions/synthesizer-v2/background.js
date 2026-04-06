// Claude Synthesizer v2 — Background service worker
// Message routing, activity logging, and DOM extraction orchestration.
'use strict';

const MAX_LOG_ENTRIES = 20;
const EXTRACTION_DELAY_MS = 3000;
const CONTENT_SCRIPT_WAIT_MS = 3000;
const EXTRACT_RETRIES = 5;

// ---------------------------------------------------------------------------
// Activity Log
// ---------------------------------------------------------------------------

async function logActivity(type, detail) {
  const storage = await chrome.storage.local.get(['activity_log']);
  const log = storage.activity_log || [];
  log.unshift({ type, detail, time: new Date().toISOString() });
  if (log.length > MAX_LOG_ENTRIES) log.length = MAX_LOG_ENTRIES;
  await chrome.storage.local.set({ activity_log: log });
  chrome.runtime.sendMessage({ action: 'LOG_UPDATED', log }).catch(() => {});
}

// ---------------------------------------------------------------------------
// Tab Helpers
// ---------------------------------------------------------------------------

function waitForTabLoad(tabId) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error('Tab load timeout'));
    }, 30_000);

    function listener(id, info) {
      if (id === tabId && info.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(listener);
        clearTimeout(timeout);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

function sendTabMessage(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, response => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response);
      }
    });
  });
}

async function extractFromTab(tabId) {
  for (let attempt = 0; attempt < EXTRACT_RETRIES; attempt++) {
    try {
      const response = await sendTabMessage(tabId, { action: 'EXTRACT_CHAT' });
      if (response?.error) throw new Error(response.error);
      // Retry if page loaded but messages haven't rendered yet
      if (!response.messages || response.messages.length === 0) {
        if (attempt < EXTRACT_RETRIES - 1) {
          await new Promise(r => setTimeout(r, CONTENT_SCRIPT_WAIT_MS));
          continue;
        }
      }
      return response;
    } catch (e) {
      if (attempt < EXTRACT_RETRIES - 1) {
        await new Promise(r => setTimeout(r, CONTENT_SCRIPT_WAIT_MS));
      } else {
        throw e;
      }
    }
  }
}

function findActiveClaudeTab(tabs) {
  if (tabs.length === 0) return null;
  return tabs.find(t => t.status === 'complete') || null;
}

// ---------------------------------------------------------------------------
// Extraction Orchestration
// ---------------------------------------------------------------------------
// Two modes:
//   download: true  -- formats output and triggers file download (Extract button)
//   download: false -- returns per-chat data for the synthesis pipeline

async function runExtraction({ download = true } = {}) {
  const storage = await chrome.storage.local.get([
    'synth_project_id', 'synth_project_name',
  ]);
  const projectId = storage.synth_project_id;
  if (!projectId) return { success: false, error: 'no_project_configured' };

  const tabs = await chrome.tabs.query({ url: 'https://claude.ai/*' });
  const activeTab = findActiveClaudeTab(tabs);
  if (!activeTab) return { success: false, error: 'no_claude_tab' };

  let convos;
  try {
    convos = await sendTabMessage(activeTab.id, {
      action: 'GET_PROJECT_CONVERSATIONS',
    });
  } catch (e) {
    return { success: false, error: 'failed_to_list_conversations: ' + e.message };
  }

  if (!convos?.conversations?.length) {
    return { success: false, error: 'no_conversations_found' };
  }

  // Filter out the synthesis temp chat, sort oldest to newest
  const chatsToExtract = convos.conversations
    .filter(c => {
      const name = (c.name || '').toLowerCase();
      return !name.includes('exclude for synthesis');
    })
    .sort((a, b) => new Date(a.updated_at || a.created_at) - new Date(b.updated_at || b.created_at));

  if (chatsToExtract.length === 0) {
    return { success: false, error: 'no_chats_to_extract' };
  }

  await logActivity('extraction', `Extracting ${chatsToExtract.length} chats...`);

  const win = await chrome.windows.create({
    url: `https://claude.ai/chat/${chatsToExtract[0].uuid}`,
    focused: false,
    type: 'normal',
  });
  const extractionTabId = win.tabs[0].id;

  const results = [];

  try {
    for (let i = 0; i < chatsToExtract.length; i++) {
      const chat = chatsToExtract[i];

      if (i > 0) {
        await chrome.tabs.update(extractionTabId, {
          url: `https://claude.ai/chat/${chat.uuid}`,
        });
      }

      await waitForTabLoad(extractionTabId);
      // Wait for content script to load, then wait for messages to render
      await new Promise(r => setTimeout(r, 1000));
      try {
        await sendTabMessage(extractionTabId, { action: 'WAIT_FOR_MESSAGES' });
      } catch {
        // Content script not ready yet, brief wait and continue to extract
        await new Promise(r => setTimeout(r, CONTENT_SCRIPT_WAIT_MS));
      }

      try {
        const data = await extractFromTab(extractionTabId);
        results.push({
          name: chat.name || data.title || 'Untitled',
          messages: data.messages,
        });
        await logActivity(
          'extraction_step',
          `${chat.name}: ${data.messages.length} messages`
        );
      } catch (e) {
        results.push({ name: chat.name || 'Untitled', error: e.message });
        await logActivity('extraction_failed', `${chat.name}: ${e.message}`);
      }

      if (i < chatsToExtract.length - 1) {
        await new Promise(r => setTimeout(r, EXTRACTION_DELAY_MS));
      }
    }
  } finally {
    try { await chrome.windows.remove(win.id); } catch {}
  }

  const successCount = results.filter(r => !r.error).length;
  const chatData = results.filter(r => !r.error);

  if (download) {
    const output = formatExtractionForDownload(results, storage.synth_project_name);
    const dateStr = new Date().toISOString().slice(0, 10);
    try {
      await sendTabMessage(activeTab.id, {
        action: 'DOWNLOAD_TEXT',
        content: output,
        filename: `synthesis-extraction-${dateStr}.txt`,
      });
    } catch (e) {
      await logActivity('extraction_failed', `Download failed: ${e.message}`);
    }
  }

  await logActivity(
    'extraction_complete',
    `${successCount}/${results.length} chats extracted`
  );

  return {
    success: successCount > 0,
    chatCount: successCount,
    totalChats: results.length,
    chatData,
    activeTabId: activeTab.id,
  };
}

function formatExtractionForDownload(results, projectName) {
  const timestamp = new Date().toLocaleString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
  });

  let output = `# Synthesis Extraction\n`;
  output += `# Project: ${projectName || 'Unknown'}\n`;
  output += `# Extracted: ${timestamp}\n`;
  output += `# Chats: ${results.filter(r => !r.error).length} of ${results.length}\n\n`;

  for (const chat of results) {
    if (chat.error) {
      output += `=== Chat: ${chat.name} (FAILED: ${chat.error}) ===\n\n`;
      continue;
    }

    const userCount = chat.messages.filter(m => m.role === 'user').length;
    const claudeCount = chat.messages.filter(m => m.role === 'assistant').length;
    output += `=== Chat: ${chat.name} (${userCount} user, ${claudeCount} claude) ===\n\n`;

    for (const msg of chat.messages) {
      if (msg.role === 'user') {
        output += `[USER] ${msg.text}\n\n`;
      } else {
        if (msg.thinking && msg.thinking.length > 0) {
          for (const t of msg.thinking) {
            const content = t.text || t.summary || '';
            if (content) output += `[THINKING] ${content}\n\n`;
          }
        }
        output += `[CLAUDE] ${msg.text}\n\n`;
      }
      output += `---\n\n`;
    }
  }

  return output;
}

// ---------------------------------------------------------------------------
// v2 Synthesis: Extract then hand off to content script
// ---------------------------------------------------------------------------

async function triggerV2Synthesis(options = {}) {
  await logActivity('synthesis', 'Starting v2 synthesis...');

  // Phase 1: Extract chats from DOM
  const extraction = await runExtraction({ download: false });
  if (!extraction.success) {
    await logActivity('synthesis_failed', `Extraction failed: ${extraction.error}`);
    return { success: false, error: extraction.error };
  }

  await logActivity(
    'synthesis_step',
    `Extracted ${extraction.chatCount} chats, starting pipeline...`
  );

  // Phase 2-5: Hand off to content script (orchestrator)
  try {
    await sendTabMessage(extraction.activeTabId, {
      action: 'RUN_V2_PIPELINE',
      chatData: extraction.chatData,
      options,
    });
  } catch (e) {
    await logActivity('synthesis_failed', 'Could not reach content script: ' + e.message);
    return { success: false, error: e.message };
  }

  return { started: true };
}

// ---------------------------------------------------------------------------
// Message Handler
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'TRIGGER_SYNTHESIZE') {
    triggerV2Synthesis(message.options).then(result => sendResponse(result));
    return true;
  }

  if (message.action === 'EXTRACT_SINGLE_CHAT') {
    (async () => {
      try {
        const win = await chrome.windows.create({
          url: `https://claude.ai/chat/${message.chatUuid}`,
          focused: false,
          type: 'normal',
        });
        const tabId = win.tabs[0].id;
        await waitForTabLoad(tabId);
        await new Promise(r => setTimeout(r, CONTENT_SCRIPT_WAIT_MS));
        const data = await extractFromTab(tabId);
        try { await chrome.windows.remove(win.id); } catch {}
        sendResponse({
          success: true,
          messages: data.messages,
          title: data.title,
        });
      } catch (e) {
        sendResponse({ success: false, error: e.message });
      }
    })();
    return true;
  }

  if (message.action === 'TRIGGER_EXTRACTION') {
    runExtraction({ download: true }).then(result => {
      chrome.runtime.sendMessage({
        action: 'EXTRACTION_COMPLETE', result,
      }).catch(() => {});
      sendResponse(result);
    });
    return true;
  }

  if (message.action === 'SYNTHESIS_COMPLETE') {
    const r = message.result;
    if (r.success) {
      logActivity('synthesis_complete', r.detail || `Done (${r.totalElapsed})`);
    } else {
      logActivity('synthesis_failed', r.error || 'unknown');
    }
    chrome.storage.local.set({ last_synthesis_result: r });
    return false;
  }

  if (message.action === 'SYNTHESIS_PROGRESS') {
    logActivity('synthesis_step', message.detail || message.phase);
    return false;
  }

  if (message.action === 'SYNTHESIS_STEP_DONE') {
    logActivity('synthesis_step_done', message.detail);
    return false;
  }

  if (message.action === 'GET_ACTIVITY_LOG') {
    chrome.storage.local.get(['activity_log'], result => {
      sendResponse({ log: result.activity_log || [] });
    });
    return true;
  }

  return false;
});
