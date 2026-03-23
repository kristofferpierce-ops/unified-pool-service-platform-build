let currentTab = "calls";
let selectedCallId = null;
let selectedSmsId = null;
let callQueue = [];
let smsQueue = [];
let selectedSmsRule = null;
let currentCallCandidates = [];
let currentSmsCandidates = [];
let currentCallDetail = null;
let currentSmsDetail = null;
let pendingConfirm = null;
let taskUsers = [];
let taskContext = null;
let queueView = "active";
let currentHudId = null;
const HELP_TEXT = {
  refresh: "Refreshes the queue right now so you can see any new calls or text summaries without waiting for auto-refresh.",
  runEod: "Creates or refreshes end-of-day text summaries for open text threads. Use this when you want today's messages grouped and summarized now.",
  reloadSuggestions: "Re-runs the CRM matching logic for this item. Use this after a new clue appears or after you change a routing rule.",
  callSearch: "Search Less Annoying CRM manually by owner name, property address, condo name, unit, or company.",
  smsSearch: "Search Less Annoying CRM manually by owner name, property address, condo name, unit, or company.",
  forceBatch: "Rebuilds the selected text summary using the messages currently saved for this thread.",
  manualRule: "Keeps this number in manual-review mode so staff chooses the correct property or contact before anything is saved.",
  attachCall: "Saves this call summary to the selected CRM contact. Use this when you know this is the right profile.",
  attachSms: "Saves this text summary to the selected CRM contact. Use this when you know this is the right profile.",
  autoHomeowner: "Marks this number as a homeowner number. Future conversations from this number will prefer this one CRM profile automatically.",
  savePm: "Keeps this number in manual mode, but remembers this property as a common match for future calls or texts from this number.",
  createTask: "Creates a follow-up task in Less Annoying CRM for the selected contact using this conversation as context.",
  trashItem: "Hides this item from the queue without saving it to CRM. Use this for spam, robocalls, or promotional messages that should not stay in the working queue."
};
async function getJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return await res.json();
}
function fmt(value) {
  if (!value) return "";
  try { return new Date(value).toLocaleString(); } catch { return value; }
}
function localDateInputValue(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}
function detectUrgency(...parts) {
  const text = parts.filter(Boolean).join(" \n ").toLowerCase();
  const urgentKeywords = ["urgent", "asap", "leak", "leaking", "flood", "pump off", "not working", "no heat", "heater", "guest complaint", "green pool", "spa down", "today"];
  return urgentKeywords.some(word => text.includes(word));
}
function buildTaskDescription(detail, type) {
  const chunks = [];
  const sourceLabel = type === "calls" ? ((detail?.item_type === 'voicemail') ? 'Voicemail' : 'Call') : 'Text summary';
  chunks.push(`Source: ${sourceLabel}`);
  if (type === "calls") {
    if (detail?.caller_phone) chunks.push(`Phone: ${detail.caller_phone}`);
    if (detail?.call_time) chunks.push(`Time: ${fmt(detail.call_time)}`);
  } else {
    if (detail?.external_phone) chunks.push(`Phone: ${detail.external_phone}`);
    if (detail?.batch_date) chunks.push(`Batch date: ${detail.batch_date}`);
  }
  if (detail?.summary) chunks.push(`
Summary:
${detail.summary}`);
  if (detail?.next_steps) chunks.push(`
Next steps:
${detail.next_steps}`);
  if (detail?.extracted_address) chunks.push(`
Address clue: ${detail.extracted_address}`);
  if (detail?.extracted_names) chunks.push(`Name clues: ${detail.extracted_names}`);
  return chunks.join("\n").trim();
}
function deriveTaskDefaults(detail, type, contact) {
  const urgent = detectUrgency(detail?.summary, detail?.next_steps, detail?.transcript, detail?.extracted_address, detail?.extracted_names);
  const phone = type === "calls" ? (detail?.caller_phone || "caller") : (detail?.external_phone || "texter");
  const address = detail?.extracted_address || "";
  const primaryNextStep = derivePrimaryNextStep(detail, type);
  const titleBase = type === "calls" ? `Follow up on call from ${phone}` : `Follow up on text from ${phone}`;
  const fallbackTitle = address ? `${titleBase} — ${address}` : titleBase;
  return {
    name: primaryNextStep || fallbackTitle,
    due_date: localDateInputValue(0),
    description: buildTaskDescription(detail, type),
    urgent,
    contact
  };
}
function resolveContactForTask(type) {
  const detail = type === "calls" ? currentCallDetail : currentSmsDetail;
  const candidates = type === "calls" ? currentCallCandidates : currentSmsCandidates;
  const attached = parseIdList(detail?.attached_contact_ids);
  if (attached.length) {
    const match = findCandidateById(candidates, attached[0]);
    return { contact_id: attached[0], name: match?.name || `Contact ${attached[0]}` };
  }
  if (candidates.length) {
    return { contact_id: candidates[0].contact_id, name: candidates[0].name || `Contact ${candidates[0].contact_id}` };
  }
  return null;
}
function parseIdList(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) return parsed.map(String).filter(Boolean);
    } catch {}
    return value.split(",").map(x => String(x).trim()).filter(Boolean);
  }
  return [];
}
function findCandidateById(candidates, contactId) {
  return (candidates || []).find(x => String(x.contact_id) === String(contactId)) || null;
}
function certaintyPresentation(level) {
  if (level === "confirmed") return { label: "Confirmed", cls: "confirmed" };
  if (level === "suggested") return { label: "Suggested", cls: "suggested" };
  if (level === "multiple") return { label: "Multiple possible matches", cls: "multiple" };
  if (level === "manual") return { label: "Manual review", cls: "manual" };
  if (level === "auto") return { label: "Auto homeowner", cls: "auto" };
  return { label: "No match", cls: "unknown" };
}
function buildIdentityState(phone, candidates, attachedIds = [], routingRule = null) {
  const list = candidates || [];
  const attached = parseIdList(attachedIds);
  const defaults = routingRule && Array.isArray(routingRule.default_contact_ids) ? routingRule.default_contact_ids.map(String) : [];
  if (attached.length === 1) {
    const matched = findCandidateById(list, attached[0]);
    return {
      level: "confirmed",
      name: matched?.name || `Contact ${attached[0]}`,
      subtitle: matched?.address || (matched?.phones || []).join(", ") || "Attached to LACRM",
      note: "Confirmed by attach action",
      phone
    };
  }
  if (attached.length > 1) {
    const names = attached.slice(0, 3).map(id => findCandidateById(list, id)?.name || `Contact ${id}`);
    return {
      level: "multiple",
      name: "Multiple confirmed matches",
      subtitle: names.join(" • "),
      note: `${attached.length} contacts are attached to this item`,
      phone
    };
  }
  if (routingRule?.mode === "auto" && defaults.length === 1) {
    const matched = findCandidateById(list, defaults[0]) || list[0] || null;
    if (matched) {
      return {
        level: "confirmed",
        name: matched.name || `Contact ${defaults[0]}`,
        subtitle: matched.address || (matched.phones || []).join(", ") || "Homeowner auto rule",
        note: "Confirmed by homeowner auto rule",
        phone
      };
    }
  }
  if (!list.length) {
    return {
      level: "unknown",
      name: "No CRM match yet",
      subtitle: "Try candidate suggestions or manual search below",
      note: "",
      phone
    };
  }
  if (list.length === 1 || (Number(list[0].score || 0) >= Number((list[1] || {}).score || 0) + 25)) {
    const top = list[0];
    return {
      level: "suggested",
      name: top.name || top.contact_id,
      subtitle: top.address || (top.phones || []).join(", ") || "Top CRM match by phone/clues",
      note: "Likely CRM match",
      phone
    };
  }
  const preview = list.slice(0, 3).map(x => x.name || x.contact_id).join(" • ");
  return {
    level: "multiple",
    name: "Multiple possible matches",
    subtitle: preview,
    note: "Choose the correct contact below to confirm",
    phone
  };
}
function deriveQueueState(item, type) {
  const attached = parseIdList(item.attached_contact_ids);
  if (attached.length === 1) return { level: "confirmed", text: "Confirmed" };
  if (attached.length > 1) return { level: "multiple", text: "Multiple" };
  if (type === "texts") {
    const rule = item.routing_rule || {};
    if (rule.mode === "auto") return { level: "auto", text: "Auto homeowner" };
    if (rule.mode === "manual") return { level: "manual", text: "Manual review" };
  }
  return { level: "suggested", text: "Needs review" };
}
function renderIdentity(prefix, phone, candidates, attachedIds = [], routingRule = null) {
  const state = buildIdentityState(phone, candidates, attachedIds, routingRule);
  const box = document.getElementById(`${prefix}IdentityBox`);
  const phoneEl = document.getElementById(`${prefix}IdentityPhone`);
  const nameEl = document.getElementById(`${prefix}IdentityName`);
  const badgeEl = document.getElementById(`${prefix}IdentityBadge`);
  const subEl = document.getElementById(`${prefix}IdentitySub`);
  const noteEl = document.getElementById(`${prefix}IdentityNote`);
  const badge = certaintyPresentation(state.level);
  phoneEl.textContent = state.phone || "";
  nameEl.textContent = state.name || "";
  subEl.textContent = state.subtitle || "";
  noteEl.textContent = state.note || "";
  badgeEl.textContent = badge.label;
  badgeEl.className = `certainty-badge ${badge.cls}`;
  box.classList.remove("hidden");
}
function renderHudIdentity(item) {
  const state = buildIdentityState(item?.caller_phone || '', item?.candidates || [], [], item?.routing_rule || null);
  const badge = certaintyPresentation(state.level);
  document.getElementById('hudIdentityPhone').textContent = state.phone || '';
  document.getElementById('hudIdentityName').textContent = state.name || '';
  document.getElementById('hudIdentitySub').textContent = state.subtitle || '';
  document.getElementById('hudIdentityNote').textContent = state.note || '';
  const badgeEl = document.getElementById('hudIdentityBadge');
  badgeEl.textContent = badge.label;
  badgeEl.className = `certainty-badge ${badge.cls}`;
}
function hideIncomingHud() {
  document.getElementById('incomingHud').classList.add('hidden');
  currentHudId = null;
}
function renderIncomingHud(item) {
  if (!item) { hideIncomingHud(); return; }
  currentHudId = item.id;
  document.getElementById('incomingHud').classList.remove('hidden');
  document.getElementById('hudCallerTitle').textContent = item.caller_phone || 'Unknown caller';
  const top = item.top_contact || null;
  const property = top?.address ? `Likely property: ${top.address}` : 'No property clue yet';
  const metaBits = [item.last_status_code || item.status || 'Incoming call'];
  if (item.call_time) metaBits.push(fmt(item.call_time));
  document.getElementById('hudMeta').textContent = metaBits.join(' • ');
  renderHudIdentity(item);
  const openTaskHint = document.getElementById('hudOpenTaskHint');
  if ((item.open_task_count || 0) > 0) {
    openTaskHint.textContent = `${item.open_task_count} open follow-up item${item.open_task_count === 1 ? '' : 's'} on this profile`;
    openTaskHint.classList.remove('hidden');
  } else {
    openTaskHint.classList.add('hidden');
  }
  const hudStatusBadge = document.getElementById('hudStatusBadge');
  hudStatusBadge.textContent = (item.last_status_code || item.status || 'Ringing');
  hudStatusBadge.className = `certainty-badge ${(item.last_status_code || item.status || '').toLowerCase().includes('answer') ? 'confirmed' : 'suggested'}`;
  const historyList = document.getElementById('hudHistoryList');
  const history = item.history || [];
  if (!history.length) {
    historyList.innerHTML = `<div class="small">No CRM history found yet. ${property}</div>`;
    return;
  }
  historyList.innerHTML = history.map(entry => `
    <div class="hud-history-item">
      <div class="hud-history-head">
        <div>
          <div class="hud-history-type">${entry.type || 'History'}</div>
          <div class="hud-history-title">${entry.title || ''}</div>
          <div class="hud-history-status">${entry.status || ''}</div>
        </div>
        <div class="hud-history-when">${fmt(entry.when)}</div>
      </div>
      <div class="small">${entry.details || ''}</div>
    </div>
  `).join('');
}
async function pollIncomingHud() {
  try {
    const payload = await getJson('/api/hud/incoming-call');
    if (!payload?.active || !payload?.item) {
      hideIncomingHud();
      return;
    }
    renderIncomingHud(payload.item);
  } catch (err) {
    console.warn('HUD poll failed', err);
  }
}
async function dismissIncomingHud() {
  if (!currentHudId) { hideIncomingHud(); return; }
  try {
    await getJson(`/api/hud/incoming-call/${currentHudId}/dismiss`, { method: 'POST' });
  } catch (err) {
    console.warn('HUD dismiss failed', err);
  }
  hideIncomingHud();
}

function escapeHtml(value) {
  return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
}

function safeJsonParse(value) {
  if (!value) return null;
  if (typeof value === "object") return value;
  try { return JSON.parse(value); } catch { return null; }
}

function stripHtml(value) {
  return String(value || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function isVoicemailItem(call) {
  return String(call?.item_type || "").toLowerCase() === "voicemail";
}

function isCallPendingAce(call) {
  return !isVoicemailItem(call) && ["PENDING_INSIGHTS", "PENDING_ACE", "WAITING_FOR_DETAILS"].includes(String(call?.status || "").toUpperCase());
}

function getCallDisplayState(call) {
  const voicemail = isVoicemailItem(call);
  if (voicemail) {
    const waitingTranscript = !String(call?.transcript || "").trim();
    return {
      summaryTitle: "Voicemail summary",
      nextStepsTitle: "Suggested follow-up",
      transcriptTitle: "Voicemail transcript",
      summaryFallback: "No voicemail summary yet.",
      nextStepsFallback: waitingTranscript ? "Waiting for voicemail transcript from RingCentral..." : "No voicemail follow-up suggested yet.",
      transcriptFallback: waitingTranscript ? "Waiting for voicemail transcript from RingCentral..." : "No voicemail transcript yet.",
      statusText: waitingTranscript ? "Waiting for voicemail transcript" : "Ready for review",
      queueWaitingBody: waitingTranscript ? "Waiting for voicemail transcript from RingCentral..." : "Waiting for details"
    };
  }
  const pendingAce = isCallPendingAce(call) || (!String(call?.summary || "").trim() && !String(call?.transcript || "").trim());
  return {
    summaryTitle: "ACE overview",
    nextStepsTitle: "ACE next steps",
    transcriptTitle: "ACE transcript",
    summaryFallback: pendingAce ? "Waiting for ACE summary from RingCentral..." : "No ACE summary yet.",
    nextStepsFallback: pendingAce ? "Waiting for ACE action items from RingCentral..." : "No ACE next steps yet.",
    transcriptFallback: pendingAce ? "Waiting for ACE transcript from RingCentral..." : "No ACE transcript yet.",
    statusText: pendingAce ? "Pending ACE insights" : "Ready for review",
    queueWaitingBody: pendingAce ? "Waiting for ACE insights from RingCentral..." : "Waiting for details"
  };
}

function collectInsightValues(node, keys, acc = []) {
  if (node == null) return acc;
  if (Array.isArray(node)) {
    node.forEach(item => collectInsightValues(item, keys, acc));
    return acc;
  }
  if (typeof node === "object") {
    Object.entries(node).forEach(([k, v]) => {
      if (keys.includes(String(k).toLowerCase())) acc.push(v);
      collectInsightValues(v, keys, acc);
    });
  }
  return acc;
}

function flattenInsightText(value, acc = []) {
  if (value == null) return acc;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    const cleaned = stripHtml(String(value));
    if (cleaned) acc.push(cleaned);
    return acc;
  }
  if (Array.isArray(value)) {
    value.forEach(item => flattenInsightText(item, acc));
    return acc;
  }
  if (typeof value === "object") {
    if (typeof value.text === "string") {
      const cleaned = stripHtml(value.text);
      if (cleaned) acc.push(cleaned);
    }
    if (typeof value.value === "string") {
      const cleaned = stripHtml(value.value);
      if (cleaned) acc.push(cleaned);
    }
    Object.values(value).forEach(v => flattenInsightText(v, acc));
  }
  return acc;
}

function uniqueNonEmpty(list) {
  const out = [];
  list.forEach(item => {
    const cleaned = stripHtml(item || "");
    if (cleaned && !out.includes(cleaned)) out.push(cleaned);
  });
  return out;
}

function splitTextToItems(text) {
  const raw = String(text || "").trim();
  if (!raw) return [];
  const cleaned = raw
      .replace(/^ACE next steps:\s*/i, "")
      .replace(/^Suggested follow-?up:\s*/i, "")
      .replace(/^Next steps:\s*/i, "");
  const lines = cleaned
      .split(/\n+/)
      .map(line => line.replace(/^[-•*\d.)\s]+/, "").trim())
      .filter(Boolean);
  if (lines.length > 1) return uniqueNonEmpty(lines);
  return uniqueNonEmpty(cleaned.split(/(?:\s*;\s*|\s*\|\s*|\s{2,})/).map(x => x.trim()).filter(Boolean));
}

function parseAceSections(detail) {
  const raw = safeJsonParse(detail?.raw_json);
  const body = raw && typeof raw.body === "object" ? raw.body : raw;
  const summaryText = stripHtml(detail?.summary || "");
  const transcriptText = detail?.transcript || "";
  const nextStepsText = stripHtml(detail?.next_steps || "");

  const recap = uniqueNonEmpty(
      collectInsightValues(body, ["recap", "highlights", "highlight", "summarybullets", "summarypoints"])
          .flatMap(v => flattenInsightText(v, []))
  );

  const questions = uniqueNonEmpty(
      collectInsightValues(body, ["questions", "followupquestions", "keyquestions"])
          .flatMap(v => flattenInsightText(v, []))
  );

  let actionItems = uniqueNonEmpty(
      collectInsightValues(body, ["nextsteps", "actionitems", "tasks", "todos"])
          .flatMap(v => flattenInsightText(v, []))
  );

  if (!actionItems.length) actionItems = splitTextToItems(nextStepsText);

  return {
    overview: summaryText,
    recap,
    questions,
    actionItems,
    transcript: transcriptText,
  };
}

function renderBulletList(items, emptyText = "") {
  if (!items || !items.length) {
    return emptyText ? `<div class="insight-empty">${escapeHtml(emptyText)}</div>` : "";
  }
  return `<ul class="insight-list">${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderActionItems(items, type) {
  if (!items || !items.length) return `<div class="insight-empty">No action items yet.</div>`;
  return `<div class="insight-task-list">${items.map(item => `
    <div class="insight-task-item">
      <div class="insight-task-copy">${escapeHtml(item)}</div>
      <button class="secondary insight-task-btn" data-quick-task="${escapeHtml(item)}" data-quick-type="${escapeHtml(type || "calls")}">Create task</button>
    </div>`).join("")}</div>`;
}

function renderTranscriptBlock(text, emptyText) {
  const cleaned = String(text || "").trim();
  if (!cleaned) return `<div class="insight-empty">${escapeHtml(emptyText)}</div>`;
  return `<div class="transcript-pre">${escapeHtml(cleaned)}</div>`;
}

function renderCallInsightPanels(call) {
  const isVoicemail = isVoicemailItem(call);
  const display = getCallDisplayState(call);

  const summaryHeading = document.getElementById("callSummaryHeading");
  const nextHeading = document.getElementById("callNextStepsHeading");
  const transcriptHeading = document.getElementById("callTranscriptHeading");

  if (summaryHeading) summaryHeading.textContent = display.summaryTitle;
  if (nextHeading) nextHeading.textContent = display.nextStepsTitle;
  if (transcriptHeading) transcriptHeading.textContent = display.transcriptTitle;

  if (isVoicemail) {
    const summaryHtml = call.summary
        ? `<div class="insight-paragraph">${escapeHtml(call.summary)}</div>`
        : `<div class="insight-empty">No voicemail summary yet.</div>`;
    const followUpItems = splitTextToItems(call.next_steps || "");
    const nextStepsHtml = renderActionItems(followUpItems.length ? followUpItems : (call.next_steps ? [call.next_steps] : []), "calls");
    const transcriptHtml = renderTranscriptBlock(call.transcript || "", display.transcriptFallback);

    document.getElementById("callSummaryText").innerHTML = summaryHtml;
    document.getElementById("callNextStepsText").innerHTML = nextStepsHtml;
    document.getElementById("callTranscriptText").innerHTML = transcriptHtml;
    return;
  }

  const sections = parseAceSections(call);
  const summaryParts = [];
  if (sections.overview) summaryParts.push(`<div class="insight-paragraph">${escapeHtml(sections.overview)}</div>`);
  if (sections.recap.length) summaryParts.push(`<div class="insight-section"><div class="insight-section-title">Recap</div>${renderBulletList(sections.recap)}</div>`);
  if (sections.questions.length) summaryParts.push(`<div class="insight-section"><div class="insight-section-title">Questions</div>${renderBulletList(sections.questions)}</div>`);
  if (!summaryParts.length) summaryParts.push(`<div class="insight-empty">${escapeHtml(display.summaryFallback)}</div>`);

  const nextHtml = renderActionItems(sections.actionItems, "calls");
  const transcriptHtml = renderTranscriptBlock(sections.transcript, display.transcriptFallback);

  document.getElementById("callSummaryText").innerHTML = summaryParts.join("");
  document.getElementById("callNextStepsText").innerHTML = nextHtml;
  document.getElementById("callTranscriptText").innerHTML = transcriptHtml;
}

function derivePrimaryNextStep(detail, type) {
  const text = String(detail?.next_steps || "").trim();
  if (!text) return "";
  if (type === "calls" && !isVoicemailItem(detail)) {
    const sections = parseAceSections(detail);
    if (sections.actionItems.length) return sections.actionItems[0];
  }
  const items = splitTextToItems(text);
  return items[0] || text;
}

function helpChip(key) {
  const text = HELP_TEXT[key] || "Explains what this action does.";
  return `<button type="button" class="help-chip" title="${text.replace(/"/g, '&quot;')}" data-help="${text.replace(/"/g, '&quot;')}" aria-label="What does this do?">?</button>`;
}
function queueItemHtml(item, type) {
  const active = type === "calls" ? selectedCallId === item.id : selectedSmsId === item.id;
  const isVoicemail = type === "calls" && String(item.item_type || "").toLowerCase() === "voicemail";
  const phone = type === "calls" ? (item.caller_phone || "Unknown caller") : (item.external_phone || "Unknown texter");
  const state = deriveQueueState(item, type);
  const callDisplay = type === "calls" ? getCallDisplayState(item) : null;
  const subtitle = type === "calls"
      ? [
        isVoicemail ? "Voicemail" : "Call",
        fmt(item.call_time),
        callDisplay ? callDisplay.statusText : item.status,
        item.voicemail_transcription_status
      ].filter(Boolean).join(" • ")
      : [item.batch_date, item.status, item.routing_rule?.owner_type || "unknown"].filter(Boolean).join(" • ");
  const body = item.extracted_address || item.extracted_names || item.summary || item.transcript || (callDisplay ? callDisplay.queueWaitingBody : "Waiting for details");
  const urgent = detectUrgency(item.summary, item.next_steps, item.transcript, item.extracted_address, item.extracted_names);
  const trashTitle = type === "calls" ? "Dismiss this call from the queue" : "Dismiss this text batch from the queue";
  return `
    <div class="queue-item ${active ? "active" : ""}" data-id="${item.id}">
      <button class="queue-trash" data-trash-id="${item.id}" data-trash-type="${type}" title="${trashTitle}">🗑</button>
      <div class="queue-head with-trash">
        <h4>${isVoicemail ? "Voicemail — " : ""}${phone}</h4>
        <div class="queue-flags">${urgent ? '<span class="urgency-badge">Urgent</span>' : ''}<span class="certainty-badge compact ${state.level}">${state.text}</span></div>
      </div>
      <div class="small">${subtitle}</div>
      <div class="small">${String(body).slice(0, 110)}</div>
    </div>
  `;
}
function renderQueue() {
  const container = document.getElementById("queue");
  const items = currentTab === "calls" ? callQueue : smsQueue;
  document.getElementById("queueTitle").textContent = currentTab === "calls"
    ? (queueView === "processed" ? "Processed call & voicemail history" : "Pending calls & voicemails")
    : (queueView === "processed" ? "Processed text history" : "Text batches awaiting review");
  document.getElementById("viewActiveBtn").classList.toggle("active", queueView === "active");
  document.getElementById("viewActiveBtn").classList.toggle("secondary", queueView !== "active");
  document.getElementById("viewProcessedBtn").classList.toggle("active", queueView === "processed");
  document.getElementById("viewProcessedBtn").classList.toggle("secondary", queueView !== "processed");
  document.getElementById("viewActiveBtn").textContent = currentTab === "calls" ? "Active calls + VM" : "Active texts";
  document.getElementById("viewProcessedBtn").textContent = currentTab === "calls" ? "Processed history" : "Processed history";
  if (!items.length) {
    container.innerHTML = `<div class="empty">${queueView === "processed" ? "No processed items yet." : `No ${currentTab === "calls" ? "pending calls or voicemails" : "text batches"} right now.`}</div>`;
    hideDetails();
    return;
  }
  container.innerHTML = items.map(item => queueItemHtml(item, currentTab)).join("");
  document.querySelectorAll(".queue-item").forEach(el => {
    el.addEventListener("click", (evt) => {
      if (evt.target.closest('.queue-trash')) return;
      if (currentTab === "calls") selectCall(el.dataset.id);
      else selectSms(el.dataset.id);
    });
  });
  document.querySelectorAll('.queue-trash').forEach(btn => {
    btn.addEventListener('click', (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
      const type = btn.dataset.trashType;
      const id = btn.dataset.trashId;
      if (type === 'calls') trashCall(id);
      else trashSms(id);
    });
  });
}
function hideDetails() {
  document.getElementById("emptyState").classList.remove("hidden");
  document.getElementById("callDetail").classList.add("hidden");
  document.getElementById("smsDetail").classList.add("hidden");
}
function showToast(message, tone = "success") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast show ${tone}`;
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toast.className = "toast";
  }, 3200);
}
function openHelpModal(text) {
  document.getElementById("helpText").textContent = text;
  document.getElementById("helpModal").classList.remove("hidden");
}
function closeHelpModal() {
  document.getElementById("helpModal").classList.add("hidden");
}
function openConfirmModal({ title, message, confirmLabel = "Confirm", tone = "warn", onConfirm }) {
  pendingConfirm = onConfirm;
  document.getElementById("confirmTitle").textContent = title;
  document.getElementById("confirmText").textContent = message;
  const btn = document.getElementById("confirmActionBtn");
  btn.textContent = confirmLabel;
  btn.className = `confirm-btn ${tone}`;
  document.getElementById("confirmModal").classList.remove("hidden");
}
function closeConfirmModal() {
  pendingConfirm = null;
  document.getElementById("confirmModal").classList.add("hidden");
}
async function handleConfirmedAction() {
  const fn = pendingConfirm;
  closeConfirmModal();
  if (!fn) return;
  try {
    await fn();
  } catch (err) {
    showToast(`Action failed: ${err.message}`, "error");
  }
}
function setQueueView(nextView) {
  queueView = nextView === "processed" ? "processed" : "active";
  if (currentTab === "calls") selectedCallId = null;
  if (currentTab === "texts") selectedSmsId = null;
  loadQueues().catch(err => showToast(`Queue refresh failed: ${err.message}`, "error"));
}
async function loadQueues() {
  callQueue = await getJson(`/api/calls?view=${encodeURIComponent(queueView)}`);
  smsQueue = await getJson(`/api/sms/batches?view=${encodeURIComponent(queueView)}`);
  renderQueue();
  if (currentTab === "calls") {
    if (selectedCallId && !callQueue.some(x => x.id === selectedCallId)) selectedCallId = null;
    if (!selectedCallId && callQueue.length) await selectCall(callQueue[0].id);
  }
  if (currentTab === "texts") {
    if (selectedSmsId && !smsQueue.some(x => x.id === selectedSmsId)) selectedSmsId = null;
    if (!selectedSmsId && smsQueue.length) await selectSms(smsQueue[0].id);
  }
}
async function selectCall(callId) {
  currentTab = "calls";
  selectedCallId = callId;
  selectedSmsId = null;
  setTabButtons();
  renderQueue();

  const call = await getJson(`/api/calls/${callId}`);
  currentCallDetail = call;

  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("callDetail").classList.remove("hidden");
  document.getElementById("smsDetail").classList.add("hidden");

  const isVoicemail = isVoicemailItem(call);
  const callDisplay = getCallDisplayState(call);

  document.getElementById("callTitle").textContent = isVoicemail
      ? `Voicemail — ${call.caller_phone || "Unknown caller"}`
      : (call.caller_phone || "Unknown caller");

  document.getElementById("callIdentityBox").classList.add("hidden");
  document.getElementById("callMeta").textContent = [
    isVoicemail ? "Voicemail" : null,
    fmt(call.call_time),
    call.direction,
    call.internal_phone,
    call.caller_name
  ].filter(Boolean).join(" • ");

  document.getElementById("callStatusBadge").textContent =
      detectUrgency(call.summary, call.next_steps, call.transcript, call.extracted_address, call.extracted_names)
          ? `Urgent • ${callDisplay.statusText}`
          : callDisplay.statusText;

  renderCallInsightPanels(call);

  const clues = [];
  if (isVoicemail && call.voicemail_transcription_status) clues.push(`<li><strong>Voicemail transcription status:</strong> ${call.voicemail_transcription_status}</li>`);
  if (isVoicemail && call.voicemail_duration) clues.push(`<li><strong>Voicemail duration:</strong> ${call.voicemail_duration} second(s)</li>`);
  if (call.extracted_address) clues.push(`<li><strong>Address clue:</strong> ${call.extracted_address}</li>`);
  if (call.extracted_names) clues.push(`<li><strong>Name clue(s):</strong> ${call.extracted_names}</li>`);
  if (!clues.length) clues.push(`<li>No clues extracted yet.</li>`);
  document.getElementById("callCluesList").innerHTML = clues.join("");

  await loadCallCandidates(call);
}
function candidateButtons(contactId, mode, contactName = "") {
  if (mode === "sms") {
    return `
      <div class="action-stack">
        <button class="attach" data-action="attach" data-contact-id="${contactId}" data-contact-name="${contactName.replace(/"/g,'&quot;')}">Attach now</button>${helpChip("attachSms")}
      </div>
      <div class="action-stack">
        <button class="secondary" data-action="task" data-contact-id="${contactId}" data-contact-name="${contactName.replace(/"/g,'&quot;')}">Create task</button>${helpChip("createTask")}
      </div>
      <div class="action-stack">
        <button class="auto" data-action="set-auto" data-contact-id="${contactId}" data-contact-name="${contactName.replace(/"/g,'&quot;')}">Set auto homeowner</button>${helpChip("autoHomeowner")}
      </div>
      <div class="action-stack">
        <button class="favorite" data-action="save-favorite" data-contact-id="${contactId}" data-contact-name="${contactName.replace(/"/g,'&quot;')}">Save PM property</button>${helpChip("savePm")}
      </div>
    `;
  }
  return `<div class="action-stack"><button class="attach" data-action="attach" data-contact-id="${contactId}" data-contact-name="${contactName.replace(/"/g,'&quot;')}">Attach</button>${helpChip("attachCall")}</div><div class="action-stack"><button class="secondary" data-action="task" data-contact-id="${contactId}" data-contact-name="${contactName.replace(/"/g,'&quot;')}">Create task</button>${helpChip("createTask")}</div>`;
}
function matchHtml(item, mode) {
  const phones = (item.phones || []).join(", ");
  const reasons = (item.reasons || []).map(r => `<div>• ${r}</div>`).join("");
  return `
    <div class="match-row">
      <div class="match-info">
        <h4>${item.name || item.contact_id}</h4>
        <div class="small">${item.address || ""}</div>
        <div class="small">${phones}</div>
        ${item.score ? `<div class="score">Score: ${item.score}</div>` : ""}
        ${reasons ? `<div class="reason-list">${reasons}</div>` : ""}
      </div>
      <div class="match-actions">${candidateButtons(item.contact_id, mode, item.name || item.contact_id)}</div>
    </div>
  `;
}
async function loadCallCandidates(callDetail = null) {
  if (!selectedCallId) return;
  const items = await getJson(`/api/calls/${selectedCallId}/candidates`);
  currentCallCandidates = items;
  const container = document.getElementById("callCandidateList");
  container.innerHTML = items.length ? items.map(x => matchHtml(x, "call")).join("") : `<div class="empty">No suggested matches yet. Use manual search below.</div>`;
  const detail = callDetail || await getJson(`/api/calls/${selectedCallId}`);
  renderIdentity("call", detail.caller_phone || "Unknown caller", items, detail.attached_contact_ids || []);
  wireCandidateButtons("callCandidateList", "call");
}
async function manualCallSearch() {
  const q = document.getElementById("callSearchInput").value.trim();
  if (!q) return;
  const items = await getJson(`/api/lacrm/search?q=${encodeURIComponent(q)}`);
  const container = document.getElementById("callSearchResults");
  container.innerHTML = items.length ? items.map(x => matchHtml(x, "call")).join("") : `<div class="empty">No LACRM results found.</div>`;
  if (items.length) { renderIdentity("call", document.getElementById("callTitle").textContent, items, []); }
  wireCandidateButtons("callSearchResults", "call");
}
async function selectSms(batchId) {
  currentTab = "texts";
  selectedSmsId = batchId;
  selectedCallId = null;
  setTabButtons();
  renderQueue();
  const batch = await getJson(`/api/sms/batches/${batchId}`);
  currentSmsDetail = batch;
  selectedSmsRule = batch.routing_rule || null;
  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("callDetail").classList.add("hidden");
  document.getElementById("smsDetail").classList.remove("hidden");
  document.getElementById("smsTitle").textContent = batch.external_phone || "Unknown texter";
  document.getElementById("smsIdentityBox").classList.add("hidden");
  document.getElementById("smsMeta").textContent = [batch.batch_date, fmt(batch.latest_message_at), batch.internal_phone].filter(Boolean).join(" • ");
  document.getElementById("smsStatusBadge").textContent = detectUrgency(batch.summary, batch.next_steps, batch.transcript, batch.extracted_address, batch.extracted_names) ? `Urgent • ${batch.status || 'Ready'}` : (batch.status || "");
  document.getElementById("smsSummaryText").textContent = batch.summary || "No batch summary yet. Use Force batch now to summarize the current day thread.";
  document.getElementById("smsNextStepsText").textContent = batch.next_steps || "No next steps yet.";
  document.getElementById("smsTranscriptText").textContent = batch.transcript || (batch.messages || []).map(m => `[${fmt(m.message_time)}] ${m.direction}: ${m.body}`).join("\n") || "No messages yet.";
  const clues = [];
  if (batch.extracted_address) clues.push(`<li><strong>Address clue:</strong> ${batch.extracted_address}</li>`);
  if (batch.extracted_names) clues.push(`<li><strong>Name clue(s):</strong> ${batch.extracted_names}</li>`);
  if (!clues.length) clues.push(`<li>No clues extracted yet.</li>`);
  document.getElementById("smsCluesList").innerHTML = clues.join("");
  renderRuleSummary(batch.routing_rule || { phone: batch.external_phone, mode: "manual", owner_type: "unknown", default_contact_ids: []});
  await loadSmsCandidates(batch);
}
function renderRuleSummary(rule) {
  selectedSmsRule = rule;
  const defaults = (rule.default_contact_ids || []).length ? (rule.default_contact_ids || []).join(", ") : "none";
  document.getElementById("routingRuleSummary").innerHTML = `
    <strong>Phone:</strong> ${rule.phone || ""}<br>
    <strong>Mode:</strong> ${rule.mode || "manual"}<br>
    <strong>Type:</strong> ${rule.owner_type || "unknown"}<br>
    <strong>Saved default/favorite contact IDs:</strong> ${defaults}
  `;
}
async function loadSmsCandidates(batchDetail = null) {
  if (!selectedSmsId) return;
  const items = await getJson(`/api/sms/batches/${selectedSmsId}/candidates`);
  currentSmsCandidates = items;
  const container = document.getElementById("smsCandidateList");
  container.innerHTML = items.length ? items.map(x => matchHtml(x, "sms")).join("") : `<div class="empty">No suggested matches yet. Use manual search below.</div>`;
  const detail = batchDetail || await getJson(`/api/sms/batches/${selectedSmsId}`);
  renderIdentity("sms", detail.external_phone || "Unknown texter", items, detail.attached_contact_ids || [], detail.routing_rule || selectedSmsRule);
  wireCandidateButtons("smsCandidateList", "sms");
}
async function manualSmsSearch() {
  const q = document.getElementById("smsSearchInput").value.trim();
  if (!q) return;
  const items = await getJson(`/api/lacrm/search?q=${encodeURIComponent(q)}`);
  const container = document.getElementById("smsSearchResults");
  container.innerHTML = items.length ? items.map(x => matchHtml(x, "sms")).join("") : `<div class="empty">No LACRM results found.</div>`;
  if (items.length) { renderIdentity("sms", document.getElementById("smsTitle").textContent, items, [], selectedSmsRule); }
  wireCandidateButtons("smsSearchResults", "sms");
}
async function updateSmsRule(newRule) {
  const rule = await getJson(`/api/routing-rules`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(newRule)
  });
  renderRuleSummary(rule);
  if (selectedSmsId) { renderIdentity("sms", document.getElementById("smsTitle").textContent, currentSmsCandidates, [], rule); }
  await loadQueues();
  return rule;
}
async function setManualRule() {
  if (!selectedSmsRule) return;
  openConfirmModal({
    title: "Require manual approval for this number?",
    message: "Future conversations from this phone number will stay in manual-review mode, so staff must choose the right contact or property before anything is confirmed.",
    confirmLabel: "Keep manual review",
    tone: "warn",
    onConfirm: async () => {
      await updateSmsRule({
        phone: selectedSmsRule.phone,
        mode: "manual",
        owner_type: "property_manager",
        default_contact_ids: selectedSmsRule.default_contact_ids || [],
        label: selectedSmsRule.label || "",
        notes: selectedSmsRule.notes || ""
      });
      showToast("This number now requires manual approval.");
    }
  });
}
async function handleSmsAction(action, contactId) {
  if (!selectedSmsId) return;
  const batch = await getJson(`/api/sms/batches/${selectedSmsId}`);
  const phone = batch.external_phone;
  if (action === "attach") {
    openConfirmModal({
      title: "Attach this text summary now?",
      message: "This will save the summary to the selected CRM contact. Use this when you are confident the thread belongs to this profile.",
      confirmLabel: "Attach summary",
      tone: "confirm",
      onConfirm: async () => {
        await getJson(`/api/sms/batches/${selectedSmsId}/attach`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({contact_ids: [contactId]})
        });
        queueView = "processed";
        await loadQueues();
        await selectSms(selectedSmsId);
        showToast("Text summary attached to LACRM and moved to processed history.");
        await promptTaskAfterAttach('texts', contactId, (findCandidateById(currentSmsCandidates, contactId) || {}).name || `Contact ${contactId}`);
      }
    });
  } else if (action === "task") {
    await openTaskModal('texts', { contact_id: contactId, name: (findCandidateById(currentSmsCandidates, contactId) || {}).name || `Contact ${contactId}` });
  } else if (action === "set-auto") {
    openConfirmModal({
      title: "Set this number as auto homeowner?",
      message: "Future conversations from this number will prefer this homeowner profile automatically. Use this only when this phone number reliably belongs to one homeowner.",
      confirmLabel: "Set auto homeowner",
      tone: "confirm",
      onConfirm: async () => {
        await updateSmsRule({
          phone,
          mode: "auto",
          owner_type: "homeowner",
          default_contact_ids: [contactId],
          label: selectedSmsRule?.label || "",
          notes: selectedSmsRule?.notes || ""
        });
        await getJson(`/api/sms/batches/${selectedSmsId}/force_batch`, { method: "POST" });
        await loadQueues();
        await selectSms(selectedSmsId);
        showToast("Saved as homeowner auto-attach and refreshed the current batch.");
      }
    });
  } else if (action === "save-favorite") {
    openConfirmModal({
      title: "Save this as a preferred PM property?",
      message: "This keeps the number in manual mode but remembers this property as a common match for future calls or texts from the same property manager.",
      confirmLabel: "Save PM property",
      tone: "confirm",
      onConfirm: async () => {
        const existing = new Set((selectedSmsRule?.default_contact_ids || []).map(String));
        existing.add(String(contactId));
        await updateSmsRule({
          phone,
          mode: "manual",
          owner_type: "property_manager",
          default_contact_ids: Array.from(existing),
          label: selectedSmsRule?.label || "",
          notes: selectedSmsRule?.notes || ""
        });
        await loadQueues();
        await selectSms(selectedSmsId);
        showToast("Saved as a preferred property for this property-manager number.");
      }
    });
  }
}
function wireCandidateButtons(containerId, mode) {
  document.querySelectorAll(`#${containerId} button[data-action]`).forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const action = btn.dataset.action;
        if (mode === "call" && action === 'attach') {
          openConfirmModal({
            title: "Attach this call now?",
            message: "This will save the call summary to the selected CRM contact. Use this when you are confident the call belongs to this profile.",
            confirmLabel: "Attach call",
            tone: "confirm",
            onConfirm: async () => {
              await getJson(`/api/calls/${selectedCallId}/attach`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({contact_ids: [btn.dataset.contactId]})
              });
              queueView = "processed";
              await loadQueues();
              await selectCall(selectedCallId);
              showToast("Call attached to LACRM and moved to processed history.");
              await promptTaskAfterAttach('calls', btn.dataset.contactId, btn.dataset.contactName || `Contact ${btn.dataset.contactId}`);
            }
          });
        } else if (mode === "call" && action === 'task') {
          await openTaskModal('calls', { contact_id: btn.dataset.contactId, name: btn.dataset.contactName || `Contact ${btn.dataset.contactId}` });
        } else {
          await handleSmsAction(action, btn.dataset.contactId);
        }
      } catch (err) {
        showToast(`Action failed: ${err.message}`, "error");
      } finally {
        btn.disabled = false;
      }
    });
  });
}
async function loadTaskUsers() {
  if (taskUsers.length) return taskUsers;
  taskUsers = await getJson('/api/lacrm/users');
  return taskUsers;
}
function fillTaskUserOptions(selectedUserId = '') {
  const select = document.getElementById('taskAssignedToSelect');
  const users = taskUsers || [];
  select.innerHTML = `<option value="">Assign to me / default user</option>` + users.map(user => `<option value="${user.user_id}">${user.name}</option>`).join('');
  if (selectedUserId) select.value = selectedUserId;
}
function closeTaskModal() {
  taskContext = null;
  document.getElementById('taskModal').classList.add('hidden');
}
async function openTaskModal(type, explicitContact = null, preset = '') {
  const detail = type === 'calls' ? currentCallDetail : currentSmsDetail;
  if (!detail) {
    showToast('Open a call or text first.', 'error');
    return;
  }
  const contact = explicitContact || resolveContactForTask(type);
  if (!contact?.contact_id) {
    showToast('Pick or attach a CRM contact first so the task has somewhere to go.', 'error');
    return;
  }
  await loadTaskUsers();
  taskContext = { type, detail, contact };
  const defaults = deriveTaskDefaults(detail, type, contact);
  document.getElementById('taskModalTitle').textContent = type === 'calls' ? 'Create call follow-up task' : 'Create text follow-up task';
  document.getElementById('taskContextType').textContent = type === 'calls' ? `Call — ${detail.caller_phone || 'Unknown caller'}` : `Text — ${detail.external_phone || 'Unknown texter'}`;
  document.getElementById('taskContextContact').textContent = `${contact.name || contact.contact_id} (${contact.contact_id})`;
  document.getElementById('taskNameInput').value = defaults.name;
  document.getElementById('taskDueDateInput').value = defaults.due_date;
  document.getElementById('taskDescriptionInput').value = defaults.description;
  document.getElementById('taskIncludeNextSteps').checked = true;
  fillTaskUserOptions();
  document.getElementById('taskModal').classList.remove('hidden');
  if (preset) applyTaskPreset(preset);
}
function applyTaskPreset(preset) {
  if (!taskContext) return;
  const detail = taskContext.detail;
  const phone = taskContext.type === 'calls' ? (detail.caller_phone || 'caller') : (detail.external_phone || 'texter');
  const address = detail.extracted_address ? ` — ${detail.extracted_address}` : '';
  const titleEl = document.getElementById('taskNameInput');
  if (preset === 'callback') titleEl.value = `Call back ${phone}${address}`;
  if (preset === 'schedule') titleEl.value = `Schedule service${address}`;
  if (preset === 'estimate') titleEl.value = `Send estimate${address}`;
  if (preset === 'followup') titleEl.value = `Follow up with contact${address}`;
}
async function submitTaskModal() {
  if (!taskContext) return;
  const name = document.getElementById('taskNameInput').value.trim();
  const dueDate = document.getElementById('taskDueDateInput').value;
  const assignedTo = document.getElementById('taskAssignedToSelect').value;
  let description = document.getElementById('taskDescriptionInput').value.trim();
  if (!name) {
    showToast('Task name is required.', 'error');
    return;
  }
  if (!document.getElementById('taskIncludeNextSteps').checked) {
    description = description.replace(/\n?Next steps:[\s\S]*$/i, '').trim();
  }
  const endpoint = taskContext.type === 'calls' ? `/api/calls/${selectedCallId}/task` : `/api/sms/batches/${selectedSmsId}/task`;
  await getJson(endpoint, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      contact_id: taskContext.contact.contact_id,
      name,
      due_date: dueDate || null,
      assigned_to: assignedTo || null,
      description,
    })
  });
  closeTaskModal();
  showToast('Task created in Less Annoying CRM.');
}
async function promptTaskAfterAttach(type, contactId, contactName = '') {
  openConfirmModal({
    title: 'Create a follow-up task too?',
    message: 'This can turn the conversation into an actionable task right away so nothing gets missed.',
    confirmLabel: 'Create task',
    tone: 'confirm',
    onConfirm: async () => {
      await openTaskModal(type, { contact_id: contactId, name: contactName || `Contact ${contactId}` });
    }
  });
}
async function trashCall(callId = selectedCallId) {
  if (!callId) return;
  openConfirmModal({
    title: 'Trash this call?',
    message: 'This hides the call from the working queue without saving it to CRM. Use this for spam, robocalls, or calls that should not be worked.',
    confirmLabel: 'Trash call',
    tone: 'warn',
    onConfirm: async () => {
      await getJson(`/api/calls/${callId}/trash`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ reason: 'Dismissed as spam or not actionable' })
      });
      if (selectedCallId === callId) {
        selectedCallId = null;
        currentCallDetail = null;
      }
      await loadQueues();
      hideDetails();
      showToast('Call removed from the queue.', 'info');
    }
  });
}
async function trashSms(batchId = selectedSmsId) {
  if (!batchId) return;
  openConfirmModal({
    title: 'Trash this text batch?',
    message: 'This hides the text thread from the working queue without saving it to CRM. Use this for spam, promotions, or junk threads.',
    confirmLabel: 'Trash text batch',
    tone: 'warn',
    onConfirm: async () => {
      await getJson(`/api/sms/batches/${batchId}/trash`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ reason: 'Dismissed as spam or not actionable' })
      });
      if (selectedSmsId === batchId) {
        selectedSmsId = null;
        currentSmsDetail = null;
      }
      await loadQueues();
      hideDetails();
      showToast('Text batch removed from the queue.', 'info');
    }
  });
}
async function forceSmsBatchNow() {
  if (!selectedSmsId) return;
  openConfirmModal({
    title: "Force a fresh text batch now?",
    message: "This rebuilds the selected text summary using the messages currently saved for this thread.",
    confirmLabel: "Rebuild batch",
    tone: "warn",
    onConfirm: async () => {
      await getJson(`/api/sms/batches/${selectedSmsId}/force_batch`, { method: "POST" });
      await loadQueues();
      await selectSms(selectedSmsId);
      showToast("Batch summary refreshed.");
    }
  });
}
async function runEodNow() {
  openConfirmModal({
    title: "Run end-of-day text batching now?",
    message: "This will finalize any open text threads and create or refresh their summaries for today.",
    confirmLabel: "Run end-of-day batch",
    tone: "warn",
    onConfirm: async () => {
      const res = await getJson(`/api/admin/run_sms_eod`, { method: "POST" });
      await loadQueues();
      showToast(`End-of-day batch finished. Finalized ${res.count} text batch(es).`);
    }
  });
}
function setTabButtons() {
  const callsBtn = document.getElementById("tabCalls");
  const textsBtn = document.getElementById("tabTexts");
  if (currentTab === "calls") {
    callsBtn.classList.add("active");
    callsBtn.classList.remove("secondary");
    textsBtn.classList.remove("active");
    textsBtn.classList.add("secondary");
  } else {
    textsBtn.classList.add("active");
    textsBtn.classList.remove("secondary");
    callsBtn.classList.remove("active");
    callsBtn.classList.add("secondary");
  }
}
document.getElementById("refreshBtn").addEventListener("click", loadQueues);
document.getElementById("runEodBtn").addEventListener("click", runEodNow);
document.getElementById("viewActiveBtn").addEventListener("click", () => setQueueView("active"));
document.getElementById("viewProcessedBtn").addEventListener("click", () => setQueueView("processed"));
document.getElementById("tabCalls").addEventListener("click", async () => { currentTab = "calls"; setTabButtons(); renderQueue(); if (selectedCallId) await selectCall(selectedCallId); else hideDetails(); });
document.getElementById("tabTexts").addEventListener("click", async () => { currentTab = "texts"; setTabButtons(); renderQueue(); if (selectedSmsId) await selectSms(selectedSmsId); else if (smsQueue.length) await selectSms(smsQueue[0].id); else hideDetails(); });
document.getElementById("reloadCallCandidatesBtn").addEventListener("click", loadCallCandidates);
document.getElementById("reloadSmsCandidatesBtn").addEventListener("click", loadSmsCandidates);
document.getElementById("callSearchBtn").addEventListener("click", manualCallSearch);
document.getElementById("smsSearchBtn").addEventListener("click", manualSmsSearch);
document.getElementById("forceBatchBtn").addEventListener("click", forceSmsBatchNow);
document.getElementById("setManualBtn").addEventListener("click", setManualRule);
document.getElementById("callCreateTaskBtn").addEventListener("click", () => openTaskModal('calls'));
document.getElementById("smsCreateTaskBtn").addEventListener("click", () => openTaskModal('texts'));
document.getElementById("callTrashBtn").addEventListener("click", () => trashCall());
document.getElementById("smsTrashBtn").addEventListener("click", () => trashSms());
document.getElementById('taskCloseBtn').addEventListener('click', closeTaskModal);
document.getElementById('taskCancelBtn').addEventListener('click', closeTaskModal);
document.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-quick-task]");
  if (!btn) return;
  const text = btn.getAttribute("data-quick-task") || "";
  openTaskModal("calls").then(() => {
    const field = document.getElementById("taskNameInput");
    if (field) {
      field.value = text;
      field.focus();
      field.select();
    }
  }).catch(err => showToast(`Task setup failed: ${err.message}`, "error"));
});
document.getElementById('taskCreateBtn').addEventListener('click', submitTaskModal);
document.getElementById('taskPresetCallback').addEventListener('click', () => applyTaskPreset('callback'));
document.getElementById('taskPresetSchedule').addEventListener('click', () => applyTaskPreset('schedule'));
document.getElementById('taskPresetEstimate').addEventListener('click', () => applyTaskPreset('estimate'));
document.getElementById('taskPresetFollowup').addEventListener('click', () => applyTaskPreset('followup'));
document.getElementById("callSearchInput").addEventListener("keydown", e => { if (e.key === "Enter") manualCallSearch(); });
document.getElementById("smsSearchInput").addEventListener("keydown", e => { if (e.key === "Enter") manualSmsSearch(); });
document.addEventListener('click', (e) => {
  const chip = e.target.closest('.help-chip[data-help]');
  if (!chip) return;
  e.preventDefault();
  e.stopPropagation();
  openHelpModal(chip.dataset.help || chip.title || '');
});
document.getElementById("helpCloseBtn").addEventListener("click", closeHelpModal);
document.getElementById("confirmCancelBtn").addEventListener("click", closeConfirmModal);
document.getElementById("confirmActionBtn").addEventListener("click", handleConfirmedAction);
document.getElementById("helpModal").addEventListener("click", (e) => { if (e.target.id === 'helpModal') closeHelpModal(); });
document.getElementById("confirmModal").addEventListener("click", (e) => { if (e.target.id === 'confirmModal') closeConfirmModal(); });
document.getElementById('taskModal').addEventListener('click', (e) => { if (e.target.id === 'taskModal') closeTaskModal(); });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeHelpModal();
    closeConfirmModal();
    closeTaskModal();
    dismissIncomingHud();
  }
});
document.getElementById('hudDismissBtn').addEventListener('click', dismissIncomingHud);
loadQueues();
pollIncomingHud();
setInterval(loadQueues, 10000);
setInterval(pollIncomingHud, 3000);
