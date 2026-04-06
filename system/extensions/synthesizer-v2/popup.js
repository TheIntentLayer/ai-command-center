// Claude Synthesizer v2 -- Popup script
'use strict';

const projectSelect = document.getElementById('project');
const pipelineSelect = document.getElementById('pipeline');
const keepChatCheckbox = document.getElementById('keep-chat');
const keepChatRow = document.getElementById('keep-chat-row');
const synthesizeBtn = document.getElementById('synthesize-btn');
const synthAnimation = document.getElementById('synth-animation');
const synthQuip = document.getElementById('synth-quip');
const statusEl = document.getElementById('status');
const activityLogEl = document.getElementById('activity-log');
const clearLogBtn = document.getElementById('clear-log-btn');

// --- Animation quips ---
const QUIPS = [
  // The work
  'Reading thinking blocks... the juicy stuff',
  'Tracing cross-chat connections...',
  'Cataloguing corrections... so many corrections',
  'Measuring emotional arcs...',
  'Spotting implicit commitments...',
  'Extracting the why behind the what...',
  'Following the human texture...',
  'Connecting what Ops said to what Code built...',
  'Finding decisions that should NOT be reopened...',
  'Tracking tone shifts and coffee levels...',
  'Building the cold-start handoff...',
  'Teaching a new Claude everything you know...',
  'Making sure no em dashes sneak through...',
  'Counting how many times Claude was corrected...',
  'Preserving the "ROFL" moments...',
  'Detecting who suggested sleep first...',
  // The process
  'Scanning 845 thinking blocks... this might take a sec',
  'Cross-referencing what Book said with what Ops decided...',
  'Checking if that decision was actually final...',
  'Finding the moment frustration turned to breakthrough...',
  'Verifying nobody moved files without discussing first...',
  'Looking for the corrections Claude missed the first time...',
  'Tracking who blamed the human for context degradation...',
  'Extracting the architecture that survived the argument...',
  'Finding where the conversation IS the thinking process...',
  'Separating what git log shows from what it cannot...',
  // The humor
  'No, I will not suggest you take a break...',
  'Counting em dashes... found zero (good)...',
  'Checking if anyone said "straightforward"...',
  'Looking for "profound" violations... all clear...',
  'Confirming figures are numbered by reading order...',
  'Making sure "one year" not "nine months"...',
  'Verifying nobody called it a "summary"...',
  'Checking that Urmila is never characterized as QA...',
  'Finding the part where Claude said "I was wrong"...',
  'Detecting the 4:30 AM start energy...',
  'Measuring the coffee-to-insight ratio...',
  'Locating the exact moment context degraded...',
  'Counting trust breaks per session...',
  'Finding the fire-and-forget that actually worked...',
  'Preserving your identity across sessions...',
  // The meta
  'A synthesizer synthesizing the synthesizer discussion...',
  'This is the part where the system builds itself...',
  'Reading about how Claude reads about how Claude reads...',
  'Processing the conversation about processing conversations...',
  'The thinking blocks about thinking blocks are... recursive',
  'DOM scraping the chat about DOM scraping...',
  'Polling for the marker about polling for markers...',
  'Extracting context about context extraction...',
  // The partnership
  'No rushing. Genuine thinking, not checklist mode...',
  'Being thorough because what we miss, they never know...',
  'This is not a tool running. This is a partner working...',
  'Reading between the lines of what was said and unsaid...',
  'Calibrating for where the human left off emotionally...',
  'Capturing what would be lost if these chats disappeared...',
  'Building the document that makes cold starts warm...',
  'Stories first, insights second...',
  'Including the corrections that paraphrasing would soften...',
  'Finding the implicit "I will do X tomorrow"...',
  // The products
  'Tracking commits and connecting the dots...',
  'GitaVani and ClearNews on the same day... that compression curve',
  'Capturing what matters from every conversation',
  'Mapping the V4.1 personality slice architecture...',
  'Following the PATs from seed messages to project instructions...',
  'Tracing the synthesis pipeline from $1.57/run to $0...',
  'Documenting the journey from RAG to DOM export...',
  'Capturing the Exclude chat becoming a partner...',
  // More fun
  'Still faster than the RAG pipeline...',
  'No API key needed. No GitHub Actions. $0/run...',
  'Each chat gets my full attention. Chain of Agents FTW...',
  'Fresh context window. No compaction risk...',
  'Sequential beats parallel. The research says so...',
  'Background tabs work. We tested it. Twice...',
  'The thinking blocks expand even in background tabs...',
  'All 373 expanded. Zero empty. We checked...',
  'This is what 17 minutes of synthesis looks like...',
  'Almost there... probably...',
  'The pipeline that replaced the pipeline that replaced the API...',
  'Fire and forget. Poll and detect. Ship and iterate...',
];
let quipInterval = null;

function startAnimation() {
  synthAnimation.classList.add('active');
  let quipIndex = 0;
  synthQuip.textContent = QUIPS[0];
  quipInterval = setInterval(() => {
    quipIndex = (quipIndex + 1) % QUIPS.length;
    synthQuip.textContent = QUIPS[quipIndex];
  }, 4000);
}

function stopAnimation() {
  synthAnimation.classList.remove('active');
  if (quipInterval) {
    clearInterval(quipInterval);
    quipInterval = null;
  }
}

// --- Load Projects ---

async function loadProjects() {
  projectSelect.innerHTML = '<option value="">Loading projects...</option>';

  const tabs = await chrome.tabs.query({ url: 'https://claude.ai/*' });
  if (tabs.length === 0) {
    projectSelect.innerHTML = '<option value="">Open claude.ai first</option>';
    return;
  }

  chrome.tabs.sendMessage(tabs[0].id, { action: 'LIST_PROJECTS' }, response => {
    if (chrome.runtime.lastError || !response || !response.projects) {
      projectSelect.innerHTML = '<option value="">Could not load projects</option>';
      return;
    }

    const projects = response.projects;
    if (projects.length === 0) {
      projectSelect.innerHTML = '<option value="">No projects found</option>';
      return;
    }

    projectSelect.innerHTML = '<option value="">Select a project...</option>';
    projects.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      opt.dataset.name = p.name;
      projectSelect.appendChild(opt);
    });

    chrome.storage.local.get(['synth_project_id'], result => {
      if (result.synth_project_id) {
        projectSelect.value = result.synth_project_id;
        synthesizeBtn.disabled = false;
      }
    });
  });
}

// --- Project Selection ---

projectSelect.addEventListener('change', () => {
  const selected = projectSelect.options[projectSelect.selectedIndex];
  const projectId = projectSelect.value;
  const projectName = selected?.dataset?.name || selected?.textContent || '';

  if (projectId) {
    chrome.storage.local.set({
      synth_project_id: projectId,
      synth_project_name: projectName,
    });
    synthesizeBtn.disabled = false;
  } else {
    synthesizeBtn.disabled = true;
  }
});

// --- Pipeline Selector ---

function updateKeepChatVisibility() {
  keepChatRow.style.display =
    pipelineSelect.value === 'full' ? 'block' : 'none';
}

pipelineSelect.addEventListener('change', () => {
  updateKeepChatVisibility();
  chrome.storage.local.set({ synth_pipeline: pipelineSelect.value });
});

// Restore last selected pipeline
chrome.storage.local.get(['synth_pipeline'], result => {
  if (result.synth_pipeline) {
    pipelineSelect.value = result.synth_pipeline;
  }
  updateKeepChatVisibility();
});

// --- Synthesize ---

synthesizeBtn.addEventListener('click', () => {
  synthesizeBtn.textContent = 'Running...';
  synthesizeBtn.disabled = true;
  statusEl.textContent = 'Starting...';
  statusEl.className = 'status running';
  startAnimation();

  const options = {
    stopAfter: pipelineSelect.value === 'full' ? null : pipelineSelect.value,
    keepChat: pipelineSelect.value === 'full' ? keepChatCheckbox.checked : true,
  };

  chrome.runtime.sendMessage({
    action: 'TRIGGER_SYNTHESIZE',
    options,
  }, response => {
    if (!response || response.error) {
      const msg = response?.error === 'no_claude_tab'
        ? 'Open claude.ai first'
        : response?.error === 'tab_not_ready'
          ? 'Claude.ai tab not loaded'
          : `Failed: ${response?.error || 'unknown'}`;
      statusEl.textContent = msg;
      statusEl.className = 'status error';
      synthesizeBtn.textContent = 'Synthesize';
      synthesizeBtn.disabled = false;
      stopAnimation();
    }
  });
});

// --- Progress & Completion Listeners ---

chrome.runtime.onMessage.addListener(message => {
  if (message.action === 'SYNTHESIS_PROGRESS') {
    statusEl.textContent = message.detail || message.phase || 'Processing...';
    statusEl.className = 'status running';
  }

  if (message.action === 'SYNTHESIS_COMPLETE') {
    const r = message.result;
    if (r.success) {
      statusEl.textContent = r.detail || `Synthesis complete (${r.totalElapsed})`;
      statusEl.className = 'status success';
    } else {
      statusEl.textContent = `Failed: ${r.error || 'unknown'}`;
      statusEl.className = 'status error';
    }
    synthesizeBtn.textContent = 'Synthesize';
    synthesizeBtn.disabled = false;
    stopAnimation();
  }

  if (message.action === 'LOG_UPDATED') {
    renderActivityLog(message.log);
  }
});

// --- Activity Log ---

const LOG_ICONS = {
  synthesis: '\u2728',
  synthesis_step: '\u23F3',
  synthesis_step_done: '\u2714',
  synthesis_complete: '\u2705',
  synthesis_failed: '\u274C',
  extraction: '\u{1F4E6}',
  extraction_step: '\u2714',
  extraction_failed: '\u274C',
  extraction_complete: '\u2705',
};

function renderActivityLog(log) {
  if (!log || log.length === 0) {
    activityLogEl.textContent = 'No activity yet.';
    return;
  }

  activityLogEl.innerHTML = log
    .map(entry => {
      const time = new Date(entry.time);
      const timeStr = time.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      const icon = LOG_ICONS[entry.type] || '\u2022';
      return `<div class="log-entry">${icon} <strong>${timeStr}</strong> ${entry.detail}</div>`;
    })
    .join('');
}

function loadActivityLog() {
  chrome.runtime.sendMessage({ action: 'GET_ACTIVITY_LOG' }, response => {
    renderActivityLog(response?.log);
  });
}

clearLogBtn.addEventListener('click', () => {
  chrome.storage.local.set({ activity_log: [] }, () => {
    renderActivityLog([]);
  });
});

// --- Init ---

loadProjects();
loadActivityLog();
