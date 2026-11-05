const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys')
const qrTerminal = require('qrcode-terminal')
const QRCode = require('qrcode')
const pino = require('pino')
const http = require('http')
const fs = require('fs')
const path = require('path')

const CHATBOT_URL = 'http://localhost:8003'
const PORT = 8004
const AUTH_DIR = './auth_info'
const logger = pino({ level: 'silent' })

let sock = null
let connected = false
let phoneNumber = null
let startTime = Date.now()
let reconnectAttempt = 0
let latestQR = null          // latest QR string (null when connected)
let qrTimestamp = 0          // when the QR was generated
let isResetting = false      // prevent close handler re-triggering during reset
const MAX_RECONNECT_DELAY = 60000

function stripMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')       // bold
    .replace(/\*(.+?)\*/g, '$1')            // italic
    .replace(/__(.+?)__/g, '$1')            // underline
    .replace(/\[(.+?)\]\(.+?\)/g, '$1')     // links -> text only
    .replace(/^[-*]\s+/gm, '- ')            // normalize bullets
    .replace(/^#{1,6}\s+/gm, '')            // headings
    .replace(/`(.+?)`/g, '$1')              // inline code
    .trim()
}

async function postJSON(url, data) {
  const body = JSON.stringify(data)
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url)
    const req = http.request({
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
    }, res => {
      let chunks = ''
      res.on('data', c => chunks += c)
      res.on('end', () => {
        try { resolve(JSON.parse(chunks)) } catch { resolve(chunks) }
      })
    })
    req.on('error', reject)
    req.write(body)
    req.end()
  })
}

function deleteAuthDir() {
  const authPath = path.resolve(AUTH_DIR)
  if (fs.existsSync(authPath)) {
    fs.rmSync(authPath, { recursive: true, force: true })
    console.log('[WhatsApp] Auth directory deleted')
  }
}

async function startBot() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)
  const { version } = await fetchLatestBaileysVersion()

  sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
  })

  sock.ev.on('creds.update', saveCreds)

  sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      console.log('\n[WhatsApp] Scan this QR code:\n')
      qrTerminal.generate(qr, { small: true })
      latestQR = qr
      qrTimestamp = Date.now()
    }

    if (connection === 'open') {
      connected = true
      reconnectAttempt = 0
      latestQR = null
      phoneNumber = sock.user?.id?.split(':')[0] || sock.user?.id?.split('@')[0] || 'unknown'
      console.log(`[WhatsApp] Connected as ${phoneNumber}`)
    }

    if (connection === 'close') {
      connected = false
      if (isResetting) return  // skip reconnect during manual reset
      const statusCode = lastDisconnect?.error?.output?.statusCode
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut

      if (shouldReconnect) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempt), MAX_RECONNECT_DELAY)
        reconnectAttempt++
        console.log(`[WhatsApp] Disconnected. Reconnecting in ${delay / 1000}s (attempt ${reconnectAttempt})...`)
        setTimeout(startBot, delay)
      } else {
        // Logged out — auto-reset: wipe auth and restart to get fresh QR
        console.log('[WhatsApp] Logged out. Auto-resetting for fresh QR...')
        latestQR = null
        deleteAuthDir()
        reconnectAttempt = 0
        setTimeout(startBot, 2000)
      }
    }
  })

  sock.ev.on('messages.upsert', async ({ messages: msgs, type }) => {
    if (type !== 'notify') return

    for (const msg of msgs) {
      // Skip non-relevant messages
      if (!msg.message) continue
      if (msg.key.fromMe) continue
      if (msg.key.remoteJid.endsWith('@g.us')) continue        // group
      if (msg.key.remoteJid === 'status@broadcast') continue   // status

      const text = msg.message.conversation
        || msg.message.extendedTextMessage?.text
        || ''
      if (!text.trim()) continue

      const jid = msg.key.remoteJid
      const phone = jid.replace('@s.whatsapp.net', '').replace('@lid', '')
      const sessionId = `wa_${phone}`

      console.log(`[WhatsApp] ${phone}: ${text}`)

      try {
        // Get chatbot response
        const result = await postJSON(`${CHATBOT_URL}/chat`, {
          message: text,
          session_id: sessionId,
          page_url: 'whatsapp'
        })

        const answer = stripMarkdown(result.answer || result.response || 'Sorry, I could not process your message.')
        const followUp = stripMarkdown(result.follow_up_message || '')

        // Send main reply
        await sock.sendMessage(jid, { text: answer })
        console.log(`[WhatsApp] Reply sent to ${phone}`)

        // Send follow-up as separate message (after short delay)
        if (followUp) {
          await new Promise(r => setTimeout(r, 800))
          await sock.sendMessage(jid, { text: followUp })
          console.log(`[WhatsApp] Follow-up sent to ${phone}`)
        }

        // Log to backend (full answer for history)
        const fullResponse = followUp ? answer + '\n\n' + followUp : answer
        await postJSON(`${CHATBOT_URL}/api/admin/whatsapp/messages`, {
          session_id: sessionId,
          phone,
          user_message: text,
          bot_response: fullResponse
        }).catch(err => console.error('[WhatsApp] Failed to log message:', err.message))

      } catch (err) {
        console.error(`[WhatsApp] Error processing message from ${phone}:`, err.message)
        await sock.sendMessage(jid, { text: 'Sorry, I am temporarily unavailable. Please try again shortly.' })
          .catch(() => {})
      }
    }
  })
}

// Handle /reset — disconnect, wipe auth, restart
async function handleReset() {
  console.log('[WhatsApp] Reset requested — disconnecting and wiping session...')
  isResetting = true  // prevent close handler from auto-reconnecting
  latestQR = null
  connected = false
  phoneNumber = null
  reconnectAttempt = 0

  // Close existing socket
  if (sock) {
    try { sock.end(); } catch {}
    try { sock.ws?.close(); } catch {}
    sock = null
  }

  // Delete auth directory
  deleteAuthDir()

  // Wait for socket to fully close, then restart
  await new Promise(r => setTimeout(r, 1500))
  isResetting = false
  startBot().catch(err => console.error('[WhatsApp] Restart error:', err))
}

// Status + QR + Reset HTTP server
const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return }

  if (req.url === '/status' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({
      connected,
      phone_number: phoneNumber,
      uptime: Math.floor((Date.now() - startTime) / 1000),
      has_qr: !!latestQR,
    }))
    return
  }

  if (req.url === '/qr' && req.method === 'GET') {
    if (connected) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ qr: null, connected: true, phone_number: phoneNumber }))
      return
    }
    if (!latestQR) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ qr: null, connected: false, message: 'No QR available. Try resetting.' }))
      return
    }
    try {
      const qrDataUrl = await QRCode.toDataURL(latestQR, { width: 280, margin: 2 })
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({
        qr: qrDataUrl,
        connected: false,
        timestamp: qrTimestamp,
      }))
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ error: 'Failed to generate QR image' }))
    }
    return
  }

  if (req.url === '/reset' && req.method === 'POST') {
    try {
      await handleReset()
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ status: 'ok', message: 'Session reset. Fresh QR will appear shortly.' }))
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ error: err.message }))
    }
    return
  }

  res.writeHead(404)
  res.end('Not found')
})

server.listen(PORT, () => {
  console.log(`[WhatsApp Bridge] Status server on http://localhost:${PORT}/status`)
  startBot().catch(err => console.error('[WhatsApp] Startup error:', err))
})
