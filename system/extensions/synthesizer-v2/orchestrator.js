// Claude Synthesizer v2 -- Synthesis orchestration
// Exposes window.SynthOrchestrator for use by content.js.
// Depends on window.SynthAPI (claude-api.js) and window.SynthPrompts (prompts.js).
//
// v2 Architecture:
// 1. Extract chats from DOM (background.js, passed in as chatData)
// 2. Create temp chat in the project, wait for boot
// 3. Send each chat transcript sequentially, poll for analysis markers
// 4. Send final synthesis prompt, poll for commit marker
// 5. Cleanup (delete temp chat unless keepChat is set)
//
// Pipeline control via options.stopAfter:
//   'boot'      -- stop after boot completes
//   'extract:1' -- stop after first chat analysis
//   'extract'   -- stop after all chats analyzed (before synthesis)
//   null/omit   -- full run including synthesis + cleanup
(function () {
  'use strict';

  const API = window.SynthAPI;
  const PROMPTS = window.SynthPrompts;

  const POLL_INTERVAL_MS = 15_000;           // 15 seconds between polls
  const BOOT_TIMEOUT_MS = 3 * 60_000;       // 3 minutes for boot
  const EXTRACTION_TIMEOUT_MS = 15 * 60_000; // 15 minutes per chat
  const SYNTHESIS_TIMEOUT_MS = 20 * 60_000;  // 20 minutes for final synthesis

  // --- Helpers ---

  function formatElapsed(ms) {
    const secs = Math.round(ms / 1000);
    const mins = Math.floor(secs / 60);
    const rem = secs % 60;
    return mins > 0 ? `${mins}m ${rem}s` : `${rem}s`;
  }

  function fillTemplate(template, vars) {
    let result = template;
    for (const [key, value] of Object.entries(vars)) {
      result = result.replaceAll(`{${key}}`, value);
    }
    return result;
  }

  function formatChatTranscript(messages) {
    let output = '';
    for (const msg of messages) {
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
    return output;
  }

  function notify(action, data) {
    chrome.runtime.sendMessage({ action, ...data }).catch(() => {});
  }

  // --- Generic marker poller ---

  async function pollForMarker(orgId, chatUuid, parentUuid, markerText, timeoutMs) {
    const startTime = Date.now();
    let continueSent = false;

    console.log(
      `Synthesizer: polling for "${markerText}" (timeout: ${timeoutMs / 60_000}m)`
    );

    while (Date.now() - startTime < timeoutMs) {
      await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));

      let state;
      try {
        state = await API.getConversationState(orgId, chatUuid);
      } catch {
        continue;
      }

      if (!state.assistant) continue;
      if (state.assistant.uuid === parentUuid) continue;

      if (state.assistant.text.includes(markerText)) {
        console.log(`Synthesizer: marker found -- "${markerText}"`);
        return { text: state.assistant.text, leafUuid: state.leafUuid };
      }

      // Tool-use limit: send Continue once
      if (!continueSent && state.assistant.text.includes('tool-use limit')) {
        console.log('Synthesizer: hit tool-use limit. Sending Continue...');
        notify('SYNTHESIS_PROGRESS', {
          detail: `Tool-use limit hit -- sending Continue...`,
        });
        await API.fireCompletion(
          orgId, chatUuid, state.leafUuid,
          `Continue. Complete your previous work. Your final line must include: ${markerText}`
        );
        continueSent = true;
      }

      const elapsed = Math.round((Date.now() - startTime) / 1000);
      console.log(
        `Synthesizer: polling (${elapsed}s${continueSent ? ', continue sent' : ''})`
      );
    }

    throw new Error(`Timed out waiting for: ${markerText}`);
  }

  // --- v2 Pipeline ---
  // chatData: array of { name, messages } from background.js extraction
  // options: { stopAfter, keepChat }

  async function run(chatData, options = {}) {
    const { stopAfter = null, keepChat = false } = options;

    const orgId = await API.getOrgId();

    const storage = await chrome.storage.local.get(['synth_project_id']);
    const projectId = storage.synth_project_id;
    if (!projectId) return { success: false, error: 'no_project_configured' };

    if (!chatData || chatData.length === 0) {
      return { success: false, error: 'no_chat_data' };
    }

    const synthStart = Date.now();
    let tempChatUuid = null;
    const chatList = chatData.map(c => c.name).join(', ');
    const shouldDelete = () => tempChatUuid && !keepChat && !stopAfter;

    try {
      // --- Create temp chat and boot ---

      notify('SYNTHESIS_PROGRESS', { detail: 'Creating temp chat...' });

      const tempChat = await API.createChat(orgId, projectId, 'Exclude for synthesis');
      tempChatUuid = tempChat.uuid;
      console.log(
        `Synthesizer: temp chat created (${tempChatUuid.substring(0, 8)}...)`
      );

      notify('SYNTHESIS_PROGRESS', { detail: 'Sending boot message...' });

      const bootPrompt = fillTemplate(PROMPTS.boot, {
        chat_count: String(chatData.length),
        chat_list: chatList,
      });
      await API.fireCompletion(orgId, tempChatUuid, 'root', bootPrompt);

      notify('SYNTHESIS_PROGRESS', { detail: 'Waiting for boot...' });

      const bootResult = await pollForMarker(
        orgId, tempChatUuid, 'root', 'BOOT COMPLETE', BOOT_TIMEOUT_MS
      );
      let parentUuid = bootResult.leafUuid;

      notify('SYNTHESIS_STEP_DONE', { detail: 'Boot complete' });

      if (stopAfter === 'boot') {
        return {
          success: true,
          detail: `Boot complete. Chat: ${tempChatUuid.substring(0, 8)}...`,
          totalElapsed: formatElapsed(Date.now() - synthStart),
        };
      }

      // --- Gather supplements (detailed git + AZ) ---

      notify('SYNTHESIS_PROGRESS', { detail: 'Gathering supplements...' });

      await API.fireCompletion(orgId, tempChatUuid, parentUuid, PROMPTS.supplements);

      const suppResult = await pollForMarker(
        orgId, tempChatUuid, parentUuid, 'SUPPLEMENTS COMPLETE', BOOT_TIMEOUT_MS
      );
      parentUuid = suppResult.leafUuid;

      notify('SYNTHESIS_STEP_DONE', { detail: 'Supplements loaded' });
      await new Promise(r => setTimeout(r, 500));

      // --- Sequential chat analysis ---

      for (let i = 0; i < chatData.length; i++) {
        const chat = chatData[i];
        const chatNum = i + 1;

        notify('SYNTHESIS_PROGRESS', {
          detail: `Analyzing ${chat.name}... (${chatNum}/${chatData.length})`,
        });

        const transcript = formatChatTranscript(chat.messages);
        const prompt = fillTemplate(PROMPTS.extraction, {
          chat_name: chat.name,
          chat_num: String(chatNum),
          chat_count: String(chatData.length),
          transcript,
        });

        const analysisStart = Date.now();
        console.log(
          `Synthesizer: sending ${chat.name} ` +
          `(${chat.messages.length} msgs, ${Math.round(prompt.length / 1024)}KB)`
        );

        await API.fireCompletion(orgId, tempChatUuid, parentUuid, prompt);

        const marker = `ANALYSIS COMPLETE: ${chat.name}`;
        const result = await pollForMarker(
          orgId, tempChatUuid, parentUuid, marker, EXTRACTION_TIMEOUT_MS
        );

        parentUuid = result.leafUuid;
        const elapsed = formatElapsed(Date.now() - analysisStart);

        notify('SYNTHESIS_STEP_DONE', {
          detail: `${chat.name} analyzed (${elapsed})`,
        });
        // Brief pause so the log entry writes before the next progress message
        await new Promise(r => setTimeout(r, 500));

        if (stopAfter === 'extract:1' && chatNum === 1) {
          return {
            success: true,
            detail: `First chat analyzed. Chat: ${tempChatUuid.substring(0, 8)}...`,
            totalElapsed: formatElapsed(Date.now() - synthStart),
          };
        }
      }

      if (stopAfter === 'extract') {
        return {
          success: true,
          detail: `All ${chatData.length} chats analyzed. Chat: ${tempChatUuid.substring(0, 8)}...`,
          totalElapsed: formatElapsed(Date.now() - synthStart),
        };
      }

      // --- Final synthesis ---

      notify('SYNTHESIS_PROGRESS', { detail: 'Running final synthesis...' });

      const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const timestamp = new Date().toLocaleString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
        hour: 'numeric', minute: '2-digit',
        timeZone: userTimezone, timeZoneName: 'short',
      });
      const synthesisPrompt = fillTemplate(PROMPTS.synthesis, {
        chat_count: String(chatData.length),
        chat_list: chatList,
        timestamp,
        timezone: userTimezone,
      });

      const synthesisStart = Date.now();
      await API.fireCompletion(orgId, tempChatUuid, parentUuid, synthesisPrompt);

      const synthResult = await pollForMarker(
        orgId, tempChatUuid, parentUuid, 'COMMIT SYNTHESIS:', SYNTHESIS_TIMEOUT_MS
      );

      const hashMatch = synthResult.text.match(
        /COMMIT SYNTHESIS:\s*([a-f0-9]{7,40})/
      );
      const commitHash = hashMatch ? hashMatch[1] : 'unknown';
      const synthesisElapsed = formatElapsed(Date.now() - synthesisStart);

      console.log(
        `Synthesizer: committed -- ${commitHash} (${synthesisElapsed})`
      );

      const totalElapsed = formatElapsed(Date.now() - synthStart);
      return {
        success: true,
        commitHash,
        totalElapsed,
        chatsProcessed: chatData.length,
        detail: `Synthesis complete -- ${chatData.length} chats (${totalElapsed})`,
      };

    } catch (e) {
      console.error('Synthesizer: pipeline failed --', e.message);
      return {
        success: false,
        error: e.message,
        totalElapsed: formatElapsed(Date.now() - synthStart),
      };

    } finally {
      // --- Cleanup ---
      if (shouldDelete()) {
        notify('SYNTHESIS_PROGRESS', { detail: 'Deleting temp chat...' });
        try {
          await API.deleteChat(orgId, tempChatUuid);
          console.log('Synthesizer: temp chat deleted');
        } catch (e) {
          console.error(
            'Synthesizer: failed to delete temp chat --', e.message
          );
        }
      } else if (tempChatUuid) {
        console.log('Synthesizer: temp chat kept for inspection');
      }
    }
  }

  window.SynthOrchestrator = { run, pollForMarker, formatChatTranscript, fillTemplate };
})();
