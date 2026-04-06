// Claude Synthesizer — Claude.ai API layer
// Exposes window.SynthAPI for use by orchestrator.js and content.js.
// No extension dependencies. Pure API calls, same-origin on claude.ai.
(function () {
  'use strict';

  async function getOrgId() {
    const resp = await fetch('/api/organizations');
    if (!resp.ok) throw new Error(`Organizations API: ${resp.status}`);
    const data = await resp.json();
    if (!Array.isArray(data) || data.length === 0) throw new Error('No organization found');
    return data[0].uuid;
  }

  async function listProjects(orgId) {
    const resp = await fetch(`/api/organizations/${orgId}/projects`);
    if (!resp.ok) return [];
    const data = await resp.json();
    return data.map(p => ({ id: p.uuid, name: p.name }));
  }

  async function listProjectConversations(orgId, projectId) {
    const resp = await fetch(
      `/api/organizations/${orgId}/projects/${projectId}/conversations`
    );
    if (!resp.ok) return [];
    return resp.json();
  }

  async function findExcludeChat(orgId, projectId) {
    const convos = await listProjectConversations(orgId, projectId);
    return convos.find(c =>
      c.name &&
      (c.name.toLowerCase().includes('exclude') ||
       c.name.toLowerCase().includes('synthesis'))
    ) || null;
  }

  // Single fetch for conversation state. Returns both the latest assistant
  // message and the leaf (last message, any sender). Eliminates the duplicate
  // fetch that existed when these were separate calls.
  async function getConversationState(orgId, chatUuid) {
    const resp = await fetch(
      `/api/organizations/${orgId}/chat_conversations/${chatUuid}`
    );
    if (!resp.ok) throw new Error(`Conversation API: ${resp.status}`);
    const data = await resp.json();
    const msgs = data.chat_messages || [];
    if (msgs.length === 0) return { assistant: null, leafUuid: null };

    // Walk backwards for latest assistant message
    let assistant = null;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].sender === 'assistant') {
        let text = msgs[i].text || '';
        if (!text && Array.isArray(msgs[i].content)) {
          text = msgs[i].content
            .filter(b => b.type === 'text')
            .map(b => b.text || '')
            .join('\n');
        }
        assistant = { uuid: msgs[i].uuid, text };
        break;
      }
    }

    return { assistant, leafUuid: msgs[msgs.length - 1].uuid };
  }

  // Create a new conversation in a project.
  // Client generates the UUID. Returns { uuid, name }.
  async function createChat(orgId, projectId, name) {
    const uuid = crypto.randomUUID();
    const resp = await fetch(
      `/api/organizations/${orgId}/chat_conversations`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uuid,
          name: name || '',
          model: 'claude-opus-4-6',
          project_uuid: projectId,
          is_temporary: false,
          include_conversation_preferences: true,
          enabled_imagine: true,
        }),
      }
    );

    if (!resp.ok) {
      const errText = await resp.text().catch(() => '');
      throw new Error(
        `Create chat: ${resp.status} ${errText.substring(0, 200)}`
      );
    }

    const data = await resp.json();
    return { uuid: data.uuid, name: data.name };
  }

  // Delete a conversation. Expects 204 No Content.
  // Fallback: retry with the full conversation object as body.
  async function deleteChat(orgId, chatUuid) {
    const resp = await fetch(
      `/api/organizations/${orgId}/chat_conversations/${chatUuid}`,
      {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      }
    );

    if (resp.status === 204) return;

    // Retry with full conversation object
    const convResp = await fetch(
      `/api/organizations/${orgId}/chat_conversations/${chatUuid}`
    );
    if (!convResp.ok) {
      throw new Error(`Delete chat: could not fetch for retry: ${convResp.status}`);
    }
    const convData = await convResp.json();

    const retryResp = await fetch(
      `/api/organizations/${orgId}/chat_conversations/${chatUuid}`,
      {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(convData),
      }
    );

    if (retryResp.status !== 204) {
      throw new Error(`Delete chat: ${retryResp.status}`);
    }
  }

  // Fire-and-forget: send a message to a conversation, immediately cancel
  // the SSE stream. Server-side processing continues regardless.
  async function fireCompletion(orgId, chatUuid, parentUuid, prompt) {
    const resp = await fetch(
      `/api/organizations/${orgId}/chat_conversations/${chatUuid}/completion`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          parent_message_uuid: parentUuid,
          timezone: 'America/Los_Angeles',
          locale: 'en-US',
          rendering_mode: 'messages',
          attachments: [],
          files: [],
          sync_sources: [],
        }),
      }
    );

    if (!resp.ok) {
      const errText = await resp.text().catch(() => '');
      throw new Error(
        `Completion API: ${resp.status} ${errText.substring(0, 200)}`
      );
    }

    if (resp.body) {
      resp.body.getReader().cancel().catch(() => {});
    }
  }

  window.SynthAPI = {
    getOrgId,
    listProjects,
    listProjectConversations,
    findExcludeChat,
    getConversationState,
    createChat,
    deleteChat,
    fireCompletion,
  };
})();
