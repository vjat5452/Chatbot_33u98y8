import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getEmailCampaigns, deleteEmailCampaign } from '../../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Mail, Plus, Loader2, Send, Clock, Pause, X, FileEdit, Trash2 } from 'lucide-react'

const statusConfig = {
  draft:     { color: 'bg-gray-100 text-gray-700', label: 'Draft', icon: FileEdit },
  scheduled: { color: 'bg-blue-100 text-blue-700', label: 'Scheduled', icon: Clock },
  sending:   { color: 'bg-amber-100 text-amber-700', label: 'Sending', icon: Send },
  sent:      { color: 'bg-emerald-100 text-emerald-700', label: 'Sent', icon: Send },
  paused:    { color: 'bg-orange-100 text-orange-700', label: 'Paused', icon: Pause },
  cancelled: { color: 'bg-red-100 text-red-700', label: 'Cancelled', icon: X },
}

function StatusBadge({ status }) {
  const cfg = statusConfig[status] || { color: 'bg-gray-100 text-gray-700', label: status }
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
}

function TypeBadge({ type }) {
  return type === 'warm'
    ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700">Warm</span>
    : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-sky-100 text-sky-700">Cold</span>
}

function CampaignCard({ campaign, onClick, onDelete }) {
  const openRate = campaign.sent_count > 0 ? (campaign.opened_count / campaign.sent_count * 100).toFixed(1) : 0
  const clickRate = campaign.sent_count > 0 ? (campaign.clicked_count / campaign.sent_count * 100).toFixed(1) : 0

  return (
    <Card className="cursor-pointer hover:border-primary/30 transition-colors" onClick={onClick}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm truncate">{campaign.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <TypeBadge type={campaign.campaign_type} />
              <StatusBadge status={campaign.status} />
            </div>
          </div>
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive" onClick={e => { e.stopPropagation(); onDelete(campaign.id, campaign.name) }}>
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
        {campaign.status !== 'draft' && (
          <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t">
            <div className="text-center">
              <div className="text-lg font-bold">{campaign.sent_count}</div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wide">Sent</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-emerald-600">{openRate}%</div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wide">Opened</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-blue-600">{clickRate}%</div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wide">Clicked</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function EmailCampaigns() {
  const navigate = useNavigate()
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('all')

  useEffect(() => {
    loadCampaigns()
  }, [])

  async function loadCampaigns() {
    try {
      const data = await getEmailCampaigns()
      setCampaigns(data.campaigns || [])
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  async function handleDelete(id, name) {
    if (!confirm(`Delete campaign "${name}"? This cannot be undone.`)) return
    try {
      await deleteEmailCampaign(id)
      loadCampaigns()
    } catch (e) { alert(e.message) }
  }

  const filtered = campaigns.filter(c => {
    if (tab === 'all') return true
    if (tab === 'warm') return c.campaign_type === 'warm'
    if (tab === 'cold') return c.campaign_type === 'cold'
    if (tab === 'draft') return c.status === 'draft'
    if (tab === 'sent') return c.status === 'sent'
    return true
  })

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground"><Loader2 className="w-8 h-8 animate-spin" /></div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Email Campaigns</h1>
          <p className="text-sm text-muted-foreground">Manage and monitor your email campaigns</p>
        </div>
        <Button onClick={() => navigate('/email/create')}>
          <Plus className="w-4 h-4 mr-2" /> Create Campaign
        </Button>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="mb-6">
        <TabsList>
          <TabsTrigger value="all">All ({campaigns.length})</TabsTrigger>
          <TabsTrigger value="warm">Warm</TabsTrigger>
          <TabsTrigger value="cold">Cold</TabsTrigger>
          <TabsTrigger value="draft">Drafts</TabsTrigger>
          <TabsTrigger value="sent">Sent</TabsTrigger>
        </TabsList>
      </Tabs>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Mail className="w-12 h-12 mx-auto mb-4 text-muted-foreground/30" />
            <h3 className="font-semibold mb-1">No campaigns yet</h3>
            <p className="text-sm text-muted-foreground mb-4">Create your first email campaign to get started.</p>
            <Button onClick={() => navigate('/email/create')}>
              <Plus className="w-4 h-4 mr-2" /> Create Campaign
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(c => (
            <CampaignCard key={c.id} campaign={c} onClick={() => navigate(`/email/${c.id}`)} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  )
}
