import { useState } from 'react'
import { sendDirectEmail } from '../../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Send, Loader2, CheckCircle2, AlertCircle, ChevronDown } from 'lucide-react'

export default function EmailDirectSend() {
  const [form, setForm] = useState({
    to_email: '', to_name: '', subject: '', html_body: '', text_body: '',
    from_name: '', from_email: '', reply_to: '',
  })
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState(null) // { type: 'success'|'error', message }
  const [showAdvanced, setShowAdvanced] = useState(false)

  const set = (key, val) => setForm(p => ({ ...p, [key]: val }))

  async function handleSend() {
    if (!form.to_email || !form.subject || !form.html_body) return
    setSending(true)
    setResult(null)
    try {
      await sendDirectEmail(form)
      setResult({ type: 'success', message: `Email sent to ${form.to_email}` })
      setForm(p => ({ ...p, to_email: '', to_name: '', subject: '', html_body: '', text_body: '' }))
    } catch (e) {
      setResult({ type: 'error', message: e.message || 'Send failed' })
    } finally {
      setSending(false)
    }
  }

  const canSend = form.to_email && form.subject && form.html_body && !sending

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Send Email</h1>
          <p className="text-sm text-muted-foreground">Compose and send an email directly — no template or campaign needed</p>
        </div>
      </div>

      {result && (
        <div className={`flex items-center gap-2 p-3 rounded-lg mb-4 text-sm ${
          result.type === 'success' ? 'bg-green-500/10 text-green-600' : 'bg-destructive/10 text-destructive'
        }`}>
          {result.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {result.message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Compose form */}
        <Card>
          <CardContent className="p-5 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="to_email">To Email *</Label>
                <Input id="to_email" type="email" value={form.to_email} onChange={e => set('to_email', e.target.value)} placeholder="recipient@example.com" className="mt-1" />
              </div>
              <div>
                <Label htmlFor="to_name">To Name</Label>
                <Input id="to_name" value={form.to_name} onChange={e => set('to_name', e.target.value)} placeholder="John Doe" className="mt-1" />
              </div>
            </div>

            <div>
              <Label htmlFor="subject">Subject *</Label>
              <Input id="subject" value={form.subject} onChange={e => set('subject', e.target.value)} placeholder="Your email subject" className="mt-1" />
            </div>

            <div>
              <Label>HTML Body *</Label>
              <textarea
                value={form.html_body}
                onChange={e => set('html_body', e.target.value)}
                className="w-full h-[300px] rounded-md border border-input bg-background px-3 py-2 text-sm font-mono resize-y mt-1"
                placeholder="<h1>Hello</h1><p>Your email content here...</p>"
              />
            </div>

            <div>
              <Label>Plain Text Body (optional)</Label>
              <textarea
                value={form.text_body}
                onChange={e => set('text_body', e.target.value)}
                className="w-full h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm font-mono resize-y mt-1"
                placeholder="Plain text fallback..."
              />
            </div>

            {/* Advanced options */}
            <div>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAdvanced ? '' : '-rotate-90'}`} />
                Advanced Options
              </button>
              {showAdvanced && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
                  <div>
                    <Label htmlFor="from_name">From Name</Label>
                    <Input id="from_name" value={form.from_name} onChange={e => set('from_name', e.target.value)} placeholder="Default" className="mt-1" />
                  </div>
                  <div>
                    <Label htmlFor="from_email">From Email</Label>
                    <Input id="from_email" type="email" value={form.from_email} onChange={e => set('from_email', e.target.value)} placeholder="Default" className="mt-1" />
                  </div>
                  <div>
                    <Label htmlFor="reply_to">Reply-To</Label>
                    <Input id="reply_to" type="email" value={form.reply_to} onChange={e => set('reply_to', e.target.value)} placeholder="Default" className="mt-1" />
                  </div>
                </div>
              )}
            </div>

            <Button onClick={handleSend} disabled={!canSend} className="w-full">
              {sending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              {sending ? 'Sending...' : 'Send Email'}
            </Button>
          </CardContent>
        </Card>

        {/* Live preview */}
        <Card>
          <CardHeader>
            <CardTitle>Preview</CardTitle>
            <CardDescription>Live preview of your HTML email</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border rounded-lg overflow-hidden">
              {form.subject && (
                <div className="bg-muted px-4 py-2 text-sm font-medium">Subject: {form.subject}</div>
              )}
              <iframe
                srcDoc={form.html_body || '<p style="color:#999;text-align:center;padding:40px;">Start typing to see preview...</p>'}
                className="w-full h-[400px] bg-white"
                sandbox="allow-same-origin"
                title="Email Preview"
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
