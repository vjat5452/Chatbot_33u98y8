import { useState, useEffect, useCallback } from 'react'
import { getSettings, saveSettings, getWhatsAppStatus, getWhatsAppQR, resetWhatsApp } from '../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Mail, TrendingUp, Loader2, Check, MessageSquare, RefreshCw, Smartphone, Wifi, WifiOff } from 'lucide-react'

function EmailProviderToggle({ value, onChange }) {
  return (
    <div className="flex gap-1 p-1 bg-muted rounded-lg w-fit">
      <button
        type="button"
        onClick={() => onChange('smtp')}
        className={`px-4 py-1.5 text-sm rounded-md font-medium transition-colors ${
          value === 'smtp' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        SMTP
      </button>
      <button
        type="button"
        onClick={() => onChange('microsoft')}
        className={`px-4 py-1.5 text-sm rounded-md font-medium transition-colors ${
          value === 'microsoft' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        Microsoft 365
      </button>
    </div>
  )
}

function WhatsAppSection() {
  const [status, setStatus] = useState(null)
  const [qrData, setQrData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const [polling, setPolling] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const s = await getWhatsAppStatus()
      setStatus(s)
      return s
    } catch { setStatus(null) }
  }, [])

  const fetchQR = useCallback(async () => {
    try {
      const data = await getWhatsAppQR()
      setQrData(data)
      return data
    } catch { setQrData(null) }
  }, [])

  // Initial load
  useEffect(() => {
    Promise.all([fetchStatus(), fetchQR()])
      .finally(() => { setLoading(false); setPolling(true) })
  }, [fetchStatus, fetchQR])

  // Poll every 3s — stops only when connected
  useEffect(() => {
    if (!polling) return
    const interval = setInterval(async () => {
      const s = await fetchStatus()
      if (s?.connected) {
        setPolling(false)
        setQrData(null)
      } else {
        await fetchQR()
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [polling, fetchStatus, fetchQR])

  async function handleReset() {
    setResetting(true)
    setQrData(null)
    try {
      await resetWhatsApp()
      setPolling(true)
    } catch (e) {
      console.error(e)
    } finally {
      setResetting(false)
    }
  }

  async function handleRefreshQR() {
    setPolling(true)
    await fetchQR()
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  const isConnected = status?.connected
  const bridgeDown = !status || (status.uptime === 0 && !status.connected && !status.has_qr)
  const isStarting = bridgeDown && (polling || resetting)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <div className="p-2 rounded-lg bg-muted">
            <MessageSquare className="w-4 h-4 text-muted-foreground" />
          </div>
          WhatsApp Connection
        </CardTitle>
        <CardDescription>Connect your WhatsApp account to enable the chatbot on WhatsApp</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Status banner */}
        <div className={`flex items-center justify-between p-3 rounded-lg mb-4 ${
          isConnected ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'
        }`}>
          <div className="flex items-center gap-3">
            {isConnected ? (
              <Wifi className="w-5 h-5 text-green-600" />
            ) : (
              <WifiOff className="w-5 h-5 text-amber-600" />
            )}
            <div>
              <p className={`text-sm font-medium ${isConnected ? 'text-green-700' : 'text-amber-700'}`}>
                {isConnected ? 'Connected' : isStarting ? 'Starting Bridge...' : bridgeDown ? 'Bridge Not Running' : 'Disconnected'}
              </p>
              {isConnected && status?.phone_number && (
                <p className="text-xs text-green-600 flex items-center gap-1 mt-0.5">
                  <Smartphone className="w-3 h-3" />
                  +{status.phone_number}
                </p>
              )}
            </div>
          </div>
          <Badge variant={isConnected ? "default" : "secondary"} className={
            isConnected ? 'bg-green-600' : ''
          }>
            {isConnected ? 'Active' : 'Inactive'}
          </Badge>
        </div>

        {/* QR Code section */}
        {!isConnected && (
          <div className="text-center py-4">
            {qrData?.qr ? (
              <div>
                <p className="text-sm text-muted-foreground mb-3">
                  Scan this QR code with your WhatsApp mobile app
                </p>
                <div className="inline-block p-3 bg-white rounded-xl border shadow-sm">
                  <img
                    src={qrData.qr}
                    alt="WhatsApp QR Code"
                    className="w-[250px] h-[250px]"
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-3">
                  Open WhatsApp &gt; Settings &gt; Linked Devices &gt; Link a Device
                </p>
                {polling && (
                  <p className="text-xs text-blue-600 mt-2 flex items-center justify-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Waiting for scan...
                  </p>
                )}
              </div>
            ) : (
              <div className="py-6">
                {isStarting ? (
                  <>
                    <Loader2 className="w-10 h-10 text-blue-500 mx-auto mb-3 animate-spin" />
                    <p className="text-sm text-muted-foreground mb-1">
                      Starting WhatsApp bridge...
                    </p>
                    <p className="text-xs text-muted-foreground">
                      QR code will appear automatically once the bridge is ready
                    </p>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-40" />
                    <p className="text-sm text-muted-foreground mb-1">
                      {bridgeDown
                        ? 'WhatsApp bridge service is not running'
                        : 'No QR code available'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {bridgeDown
                        ? 'Click "Reset & Reconnect" to start the bridge and generate a QR code'
                        : 'Click "Reset & Reconnect" to generate a fresh QR code'}
                    </p>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 mt-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRefreshQR}
            disabled={resetting}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${polling ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            type="button"
            variant={isConnected ? "outline" : "default"}
            size="sm"
            onClick={handleReset}
            disabled={resetting}
          >
            {resetting ? (
              <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Resetting...</>
            ) : (
              <>{isConnected ? 'Disconnect & Reset' : 'Reset & Reconnect'}</>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default function Settings() {
  const [form, setForm] = useState({
    email_provider: 'smtp',
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    ms_tenant_id: '',
    ms_client_id: '',
    ms_client_secret: '',
    ms_sender_email: '',
    alert_emails: '',
    lead_hot_threshold: 60,
    lead_qualified_threshold: 40,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings()
      .then(data => setForm(f => ({
        ...f,
        ...data,
        smtp_password: '',
        ms_client_secret: '',
      })))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    try {
      await saveSettings(form)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  function update(key, value) {
    setForm(f => ({ ...f, [key]: value }))
  }

  if (loading) return (
    <div className="text-center text-muted-foreground py-16">
      <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" />
      Loading settings...
    </div>
  )

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Configure integrations, notifications, and lead scoring</p>
      </div>

      <div className="space-y-5">
        {/* WhatsApp Connection */}
        <WhatsAppSection />

        {/* Email + Lead Scoring form */}
        <form onSubmit={handleSave} className="space-y-5">
          {/* Email Configuration */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <div className="p-2 rounded-lg bg-muted">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                  </div>
                  Email Configuration
                </CardTitle>
                <EmailProviderToggle
                  value={form.email_provider}
                  onChange={v => update('email_provider', v)}
                />
              </div>
              <CardDescription>
                {form.email_provider === 'smtp'
                  ? 'Configure SMTP server for sending emails and notifications'
                  : 'Configure Microsoft 365 / Azure AD for sending emails via Graph API'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {form.email_provider === 'smtp' ? (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">SMTP Host</Label>
                    <Input
                      value={form.smtp_host}
                      onChange={e => update('smtp_host', e.target.value)}
                      placeholder="smtp.gmail.com"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">SMTP Port</Label>
                    <Input
                      type="number"
                      value={form.smtp_port}
                      onChange={e => update('smtp_port', parseInt(e.target.value) || 587)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">SMTP User</Label>
                    <Input
                      value={form.smtp_user}
                      onChange={e => update('smtp_user', e.target.value)}
                      placeholder="alerts@sparrowi.com"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">SMTP Password</Label>
                    <Input
                      type="password"
                      autoComplete="off"
                      value={form.smtp_password}
                      onChange={e => update('smtp_password', e.target.value)}
                      placeholder="Leave blank to keep current"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Tenant ID</Label>
                      <Input
                        value={form.ms_tenant_id}
                        onChange={e => update('ms_tenant_id', e.target.value)}
                        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                      />
                    </div>
                    <div>
                      <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Client ID</Label>
                      <Input
                        value={form.ms_client_id}
                        onChange={e => update('ms_client_id', e.target.value)}
                        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Client Secret</Label>
                    <Input
                      type="password"
                      autoComplete="off"
                      value={form.ms_client_secret}
                      onChange={e => update('ms_client_secret', e.target.value)}
                      placeholder="Leave blank to keep current"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Sender Email</Label>
                    <Input
                      value={form.ms_sender_email}
                      onChange={e => update('ms_sender_email', e.target.value)}
                      placeholder="rishi.sharma@sparrowi.com"
                    />
                    <p className="text-[11px] text-muted-foreground mt-1.5">Microsoft 365 mailbox to send from (must have SendMail permission)</p>
                  </div>
                </div>
              )}

              <div className="mt-4">
                <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Alert Emails</Label>
                <Input
                  value={form.alert_emails}
                  onChange={e => update('alert_emails', e.target.value)}
                  placeholder="sales@sparrowi.com, admin@sparrowi.com"
                />
                <p className="text-[11px] text-muted-foreground mt-1.5">Comma-separated email addresses to receive hot lead alerts</p>
              </div>
            </CardContent>
          </Card>

          {/* Lead scoring */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <div className="p-2 rounded-lg bg-muted">
                  <TrendingUp className="w-4 h-4 text-muted-foreground" />
                </div>
                Lead Scoring Thresholds
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-3 block">Hot Lead Threshold</Label>
                  <div className="flex items-center gap-3">
                    <Slider
                      value={[form.lead_hot_threshold]}
                      onValueChange={([v]) => update('lead_hot_threshold', v)}
                      min={20}
                      max={100}
                      step={1}
                      className="flex-1"
                    />
                    <span className="text-sm font-bold w-8 text-right">{form.lead_hot_threshold}</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1.5">Score above this = "hot" lead + email alert</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-3 block">Qualified Lead Threshold</Label>
                  <div className="flex items-center gap-3">
                    <Slider
                      value={[form.lead_qualified_threshold]}
                      onValueChange={([v]) => update('lead_qualified_threshold', v)}
                      min={10}
                      max={80}
                      step={1}
                      className="flex-1"
                    />
                    <span className="text-sm font-bold w-8 text-right">{form.lead_qualified_threshold}</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1.5">Score above this = "qualified" lead</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Save */}
          <div className="flex items-center gap-4">
            <Button type="submit" disabled={saving}>
              {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</> : 'Save Settings'}
            </Button>
            {saved && (
              <span className="inline-flex items-center gap-1.5 text-sm text-green-600 font-medium">
                <Check className="w-4 h-4" />
                Settings saved successfully!
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
