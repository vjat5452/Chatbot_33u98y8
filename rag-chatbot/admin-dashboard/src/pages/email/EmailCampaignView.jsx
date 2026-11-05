import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { getEmailCampaign, getCampaignRecipients, getCampaignAbResults, sendEmailCampaign, pauseEmailCampaign, cancelEmailCampaign, testEmailCampaign } from '../../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Send, Pause, X, FlaskConical, Loader2, Mail, MousePointerClick, Eye, AlertTriangle } from 'lucide-react'

function StatCard({ label, value, sub, icon: Icon, color = 'text-foreground' }) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
          {Icon && <Icon className="w-4 h-4 text-muted-foreground" />}
        </div>
        <div className={`text-2xl font-bold ${color}`}>{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </CardContent>
    </Card>
  )
}

export default function EmailCampaignView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [campaign, setCampaign] = useState(null)
  const [recipients, setRecipients] = useState(null)
  const [abResults, setAbResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [testEmail, setTestEmail] = useState('')
  const [actionLoading, setActionLoading] = useState('')

  const load = useCallback(async () => {
    try {
      const c = await getEmailCampaign(id)
      setCampaign(c)
      if (c.status !== 'draft') {
        const r = await getCampaignRecipients(id, { limit: 50 })
        setRecipients(r)
      }
      if (c.ab_enabled) {
        const ab = await getCampaignAbResults(id)
        setAbResults(ab)
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [id])

  useEffect(() => { load() }, [load])

  // Auto-refresh for sending campaigns
  useEffect(() => {
    if (campaign?.status === 'sending') {
      const interval = setInterval(load, 10000)
      return () => clearInterval(interval)
    }
  }, [campaign?.status, load])

  async function handleAction(action) {
    setActionLoading(action)
    try {
      if (action === 'send') await sendEmailCampaign(id)
      else if (action === 'pause') await pauseEmailCampaign(id)
      else if (action === 'cancel') await cancelEmailCampaign(id)
      else if (action === 'test') await testEmailCampaign(id, testEmail)
      await load()
    } catch (e) { alert(e.message) }
    finally { setActionLoading('') }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>
  if (!campaign) return <div className="text-center py-16 text-muted-foreground">Campaign not found</div>

  const openRate = campaign.sent_count > 0 ? (campaign.opened_count / campaign.sent_count * 100).toFixed(1) : 0
  const clickRate = campaign.sent_count > 0 ? (campaign.clicked_count / campaign.sent_count * 100).toFixed(1) : 0
  const bounceRate = campaign.sent_count > 0 ? (campaign.bounced_count / campaign.sent_count * 100).toFixed(1) : 0

  const abChartConfig = { A: { label: 'Variant A', color: 'hsl(220 85% 50%)' }, B: { label: 'Variant B', color: 'hsl(160 60% 45%)' } }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" size="icon" onClick={() => navigate('/email')}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{campaign.name}</h1>
            <Badge variant={campaign.campaign_type === 'warm' ? 'default' : 'secondary'}>
              {campaign.campaign_type}
            </Badge>
            <Badge variant="outline">{campaign.status}</Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {campaign.status === 'draft' && (
            <>
              <div className="flex items-center gap-1">
                <Input placeholder="test@email.com" value={testEmail} onChange={e => setTestEmail(e.target.value)} className="w-48 h-9 text-sm" />
                <Button size="sm" variant="outline" onClick={() => handleAction('test')} disabled={!testEmail || actionLoading === 'test'}>
                  {actionLoading === 'test' ? <Loader2 className="w-3 h-3 animate-spin" /> : <FlaskConical className="w-3 h-3" />}
                </Button>
              </div>
              <Button onClick={() => handleAction('send')} disabled={actionLoading === 'send'}>
                {actionLoading === 'send' ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                Send Now
              </Button>
            </>
          )}
          {campaign.status === 'sending' && (
            <Button variant="outline" onClick={() => handleAction('pause')}>
              <Pause className="w-4 h-4 mr-2" /> Pause
            </Button>
          )}
          {['draft', 'scheduled', 'sending', 'paused'].includes(campaign.status) && (
            <Button variant="destructive" size="sm" onClick={() => handleAction('cancel')}>
              <X className="w-4 h-4 mr-1" /> Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <StatCard label="Sent" value={campaign.sent_count} icon={Send} />
        <StatCard label="Delivered" value={campaign.sent_count - campaign.bounced_count} icon={Mail} />
        <StatCard label="Opened" value={`${openRate}%`} sub={`${campaign.opened_count} opens`} icon={Eye} color="text-emerald-600" />
        <StatCard label="Clicked" value={`${clickRate}%`} sub={`${campaign.clicked_count} clicks`} icon={MousePointerClick} color="text-blue-600" />
        <StatCard label="Bounced" value={`${bounceRate}%`} sub={`${campaign.bounced_count} bounced`} icon={AlertTriangle} color="text-red-600" />
        <StatCard label="Unsubscribed" value={campaign.unsubscribed_count} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* A/B Results */}
        {abResults && (
          <Card>
            <CardHeader>
              <CardTitle>A/B Test Results</CardTitle>
              <CardDescription>Comparing variant performance</CardDescription>
            </CardHeader>
            <CardContent>
              <ChartContainer config={abChartConfig} className="h-[250px] w-full">
                <BarChart data={[
                  { metric: 'Open Rate', A: abResults.A?.open_rate || 0, B: abResults.B?.open_rate || 0 },
                  { metric: 'Click Rate', A: abResults.A?.click_rate || 0, B: abResults.B?.click_rate || 0 },
                ]}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="metric" tickLine={false} axisLine={false} />
                  <YAxis tickLine={false} axisLine={false} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="A" fill="var(--color-A)" radius={4} />
                  <Bar dataKey="B" fill="var(--color-B)" radius={4} />
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Recipients Table */}
      {recipients && recipients.sends && recipients.sends.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recipients ({recipients.total})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Variant</TableHead>
                  <TableHead>Opens</TableHead>
                  <TableHead>Clicks</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recipients.sends.map(s => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium text-sm">{s.recipient_email}</TableCell>
                    <TableCell className="text-sm">{s.recipient_name || '-'}</TableCell>
                    <TableCell>
                      <Badge variant={s.status === 'sent' ? 'default' : s.status === 'bounced' ? 'destructive' : 'secondary'} className="text-xs">
                        {s.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{s.ab_variant}</TableCell>
                    <TableCell className="text-sm">{s.open_count}</TableCell>
                    <TableCell className="text-sm">{s.click_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
