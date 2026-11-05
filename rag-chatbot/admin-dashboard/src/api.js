const BASE = '/api/admin'

// TTL cache for read endpoints
const _cache = new Map()

function _getAuthHeaders() {
  const token = sessionStorage.getItem('admin_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ..._getAuthHeaders(), ...options.headers },
    ...options,
  })
  if (res.status === 401) {
    // Session expired — clear and redirect to login
    sessionStorage.removeItem('admin_token')
    sessionStorage.removeItem('admin_user')
    window.location.reload()
    throw new Error('Session expired')
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json()
}

function fetchJSONCached(url, ttlMs) {
  const now = Date.now()
  const cached = _cache.get(url)
  if (cached && now - cached.ts < ttlMs) {
    return Promise.resolve(cached.data)
  }
  return fetchJSON(url).then(data => {
    _cache.set(url, { data, ts: now })
    return data
  })
}

export async function getDashboard() {
  return fetchJSONCached(`${BASE}/dashboard`, 15000)
}

export async function getLeads(params = {}) {
  const query = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') query.set(k, v)
  }
  return fetchJSON(`${BASE}/leads?${query}`)
}

export async function getLead(id) {
  return fetchJSON(`${BASE}/leads/${id}`)
}

export async function updateLead(id, data) {
  return fetchJSON(`${BASE}/leads/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function getAnalytics(days = 30) {
  // Clear cache when days changes so tabs work properly
  const url = `${BASE}/analytics?days=${days}`
  return fetchJSONCached(url, 60000)
}

export async function getRecentLeads(limit = 5) {
  return getLeads({ sort: 'created_at', order: 'desc', limit })
}

export async function getHotLeads(limit = 5) {
  return getLeads({ status: 'hot', sort: 'created_at', order: 'desc', limit })
}

export async function getConversations(params = {}) {
  const query = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') query.set(k, v)
  }
  return fetchJSON(`${BASE}/conversations?${query}`)
}

export async function getConversation(sessionId) {
  return fetchJSON(`${BASE}/conversations/${sessionId}`)
}

export async function getSettings() {
  return fetchJSON(`${BASE}/settings`)
}

export async function saveSettings(data) {
  return fetchJSON(`${BASE}/settings`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getExportUrl() {
  return `${BASE}/export/leads`
}

export async function getIssues(params = {}) {
  const query = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') query.set(k, v)
  }
  return fetchJSON(`${BASE}/issues?${query}`)
}

export async function getIssue(id) {
  return fetchJSON(`${BASE}/issues/${id}`)
}

export async function updateIssue(id, data) {
  return fetchJSON(`${BASE}/issues/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteIssue(id) {
  return fetchJSON(`${BASE}/issues/${id}`, {
    method: 'DELETE',
  })
}

// ── Golden Q&A ──

export async function getGoldenQAList(category) {
  const q = category ? `?category=${encodeURIComponent(category)}` : ''
  return fetchJSON(`${BASE}/golden-qa${q}`)
}

export async function createGoldenQA(data) {
  return fetchJSON(`${BASE}/golden-qa`, { method: 'POST', body: JSON.stringify(data) })
}

export async function updateGoldenQA(id, data) {
  return fetchJSON(`${BASE}/golden-qa/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export async function deleteGoldenQA(id) {
  return fetchJSON(`${BASE}/golden-qa/${id}`, { method: 'DELETE' })
}

export async function syncGoldenQA() {
  return fetchJSON(`${BASE}/golden-qa/sync`, { method: 'POST' })
}

// ── Email Sales System ──

// Templates
export async function getEmailTemplates(category) {
  const q = category ? `?category=${category}` : ''
  return fetchJSON(`${BASE}/email/templates${q}`)
}

export async function getEmailTemplate(id) {
  return fetchJSON(`${BASE}/email/templates/${id}`)
}

export async function createEmailTemplate(data) {
  return fetchJSON(`${BASE}/email/templates`, { method: 'POST', body: JSON.stringify(data) })
}

export async function updateEmailTemplate(id, data) {
  return fetchJSON(`${BASE}/email/templates/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export async function previewEmailTemplate(id, sampleData = {}) {
  return fetchJSON(`${BASE}/email/templates/${id}/preview`, { method: 'POST', body: JSON.stringify({ sample_data: sampleData }) })
}

export async function duplicateEmailTemplate(id) {
  return fetchJSON(`${BASE}/email/templates/${id}/duplicate`, { method: 'POST' })
}

export async function deleteEmailTemplate(id) {
  return fetchJSON(`${BASE}/email/templates/${id}`, { method: 'DELETE' })
}

// Contacts
export async function getEmailContacts(params = {}) {
  const query = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') query.set(k, v)
  }
  return fetchJSON(`${BASE}/email/contacts?${query}`)
}

export async function createEmailContact(data) {
  return fetchJSON(`${BASE}/email/contacts`, { method: 'POST', body: JSON.stringify(data) })
}

export async function updateEmailContact(id, data) {
  return fetchJSON(`${BASE}/email/contacts/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export async function importEmailContacts(file, tags = '') {
  const formData = new FormData()
  formData.append('file', file)
  if (tags) formData.append('tags', tags)
  const res = await fetch(`${BASE}/email/contacts/import?tags=${encodeURIComponent(tags)}`, {
    method: 'POST',
    headers: _getAuthHeaders(),
    body: formData,
  })
  if (res.status === 401) {
    sessionStorage.removeItem('admin_token')
    sessionStorage.removeItem('admin_user')
    window.location.reload()
    throw new Error('Session expired')
  }
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function getContactsExportUrl(status) {
  return `${BASE}/email/contacts/export${status ? `?status=${status}` : ''}`
}

export async function validateEmailContacts() {
  return fetchJSON(`${BASE}/email/contacts/validate`, { method: 'POST' })
}

export async function syncLeadsToContacts() {
  return fetchJSON(`${BASE}/email/contacts/sync-leads`, { method: 'POST' })
}

// Campaigns
export async function getEmailCampaigns(params = {}) {
  const query = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') query.set(k, v)
  }
  return fetchJSON(`${BASE}/email/campaigns?${query}`)
}

export async function getEmailCampaign(id) {
  return fetchJSON(`${BASE}/email/campaigns/${id}`)
}

export async function createEmailCampaign(data) {
  return fetchJSON(`${BASE}/email/campaigns`, { method: 'POST', body: JSON.stringify(data) })
}

export async function updateEmailCampaign(id, data) {
  return fetchJSON(`${BASE}/email/campaigns/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export async function sendEmailCampaign(id) {
  return fetchJSON(`${BASE}/email/campaigns/${id}/send`, { method: 'POST' })
}

export async function scheduleEmailCampaign(id, scheduledAt) {
  return fetchJSON(`${BASE}/email/campaigns/${id}/schedule`, { method: 'POST', body: JSON.stringify({ scheduled_at: scheduledAt }) })
}

export async function pauseEmailCampaign(id) {
  return fetchJSON(`${BASE}/email/campaigns/${id}/pause`, { method: 'POST' })
}

export async function cancelEmailCampaign(id) {
  return fetchJSON(`${BASE}/email/campaigns/${id}/cancel`, { method: 'POST' })
}

export async function testEmailCampaign(id, testEmail) {
  return fetchJSON(`${BASE}/email/campaigns/${id}/test`, { method: 'POST', body: JSON.stringify({ test_email: testEmail }) })
}

export async function getCampaignRecipients(id, params = {}) {
  const query = new URLSearchParams(params)
  return fetchJSON(`${BASE}/email/campaigns/${id}/recipients?${query}`)
}

export async function getCampaignAbResults(id) {
  return fetchJSON(`${BASE}/email/campaigns/${id}/ab-results`)
}

// Sequences
export async function getEmailSequences(campaignType) {
  const q = campaignType ? `?campaign_type=${campaignType}` : ''
  return fetchJSON(`${BASE}/email/sequences${q}`)
}

export async function getEmailSequence(id) {
  return fetchJSON(`${BASE}/email/sequences/${id}`)
}

export async function createEmailSequence(data) {
  return fetchJSON(`${BASE}/email/sequences`, { method: 'POST', body: JSON.stringify(data) })
}

export async function addSequenceStep(seqId, data) {
  return fetchJSON(`${BASE}/email/sequences/${seqId}/steps`, { method: 'POST', body: JSON.stringify(data) })
}

export async function enrollInSequence(seqId, data) {
  return fetchJSON(`${BASE}/email/sequences/${seqId}/enroll`, { method: 'POST', body: JSON.stringify(data) })
}

export async function getSequenceFunnel(seqId) {
  return fetchJSON(`${BASE}/email/sequences/${seqId}/funnel`)
}

// Email Analytics
export async function getEmailAnalyticsOverview(days = 30) {
  return fetchJSON(`${BASE}/email/analytics/overview?days=${days}`)
}

export async function getEmailWarmVsCold(days = 30) {
  return fetchJSON(`${BASE}/email/analytics/warm-vs-cold?days=${days}`)
}

export async function getEmailSendTimes(days = 90) {
  return fetchJSON(`${BASE}/email/analytics/send-times?days=${days}`)
}

export async function getEmailDomainHealth(days = 30) {
  return fetchJSON(`${BASE}/email/analytics/domains?days=${days}`)
}

export async function getEmailVolume(days = 30) {
  return fetchJSON(`${BASE}/email/analytics/volume?days=${days}`)
}

export async function getEmailRankings(days = 30) {
  return fetchJSON(`${BASE}/email/analytics/rankings?days=${days}`)
}

// Delete contacts
export async function deleteEmailContacts(ids) {
  return fetchJSON(`${BASE}/email/contacts/delete`, { method: 'POST', body: JSON.stringify({ ids }) })
}

// Delete campaign
export async function deleteEmailCampaign(id) {
  return fetchJSON(`${BASE}/email/campaigns/${id}`, { method: 'DELETE' })
}

// Direct email send
export async function sendDirectEmail(data) {
  return fetchJSON(`${BASE}/email/send`, { method: 'POST', body: JSON.stringify(data) })
}

// ── WhatsApp ──

export async function getWhatsAppStatus() {
  return fetchJSON(`${BASE}/whatsapp/status`)
}

export async function getWhatsAppQR() {
  return fetchJSON(`${BASE}/whatsapp/qr`)
}

export async function resetWhatsApp() {
  return fetchJSON(`${BASE}/whatsapp/reset`, { method: 'POST' })
}

export async function getWhatsAppConversations(page = 1, search = '') {
  const query = new URLSearchParams()
  if (page > 1) query.set('page', page)
  if (search) query.set('search', search)
  return fetchJSON(`${BASE}/whatsapp/conversations?${query}`)
}

export async function getWhatsAppChat(sessionId) {
  return fetchJSON(`${BASE}/whatsapp/conversations/${sessionId}`)
}

export async function getWhatsAppAnalytics() {
  return fetchJSON(`${BASE}/whatsapp/analytics`)
}
