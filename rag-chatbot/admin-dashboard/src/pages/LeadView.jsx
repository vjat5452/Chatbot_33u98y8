import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getLead, updateLead } from '../api'
import ChatViewer from '../components/ChatViewer'
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import { ArrowLeft, User, Loader2 } from 'lucide-react'

const statusOptions = ['new', 'engaged', 'qualified', 'hot', 'converted']

export default function LeadView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [lead, setLead] = useState(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getLead(id)
      .then(data => {
        setLead(data)
        setStatus(data.status)
        setNotes(data.notes || '')
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  async function handleSave() {
    setSaving(true)
    try {
      await updateLead(id, { status, notes })
      setLead(prev => ({ ...prev, status, notes }))
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div className="text-center text-muted-foreground py-16">
      <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" />
      Loading lead...
    </div>
  )
  if (!lead) return <div className="text-center text-muted-foreground py-16">Lead not found</div>

  return (
    <div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate('/leads')}
        className="mb-5"
      >
        <ArrowLeft className="w-4 h-4 mr-1.5" />
        Back to Leads
      </Button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Lead info */}
        <div className="lg:col-span-1 space-y-5">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-5">
                <Avatar>
                  <AvatarFallback>
                    <User className="w-5 h-5" />
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h2 className="text-lg font-semibold">
                    {lead.name || 'Unknown Lead'}
                  </h2>
                  <Badge variant="secondary" className="mt-0.5">
                    {lead.status}
                  </Badge>
                </div>
              </div>

              <div className="space-y-3">
                <InfoRow label="Email" value={lead.email} />
                <InfoRow label="Phone" value={lead.phone} />
                <InfoRow label="Company" value={lead.company} />
                <InfoRow label="Source Page" value={lead.source_page} />
                <InfoRow label="Score" value={
                  <span className="text-lg font-bold">{lead.lead_score}<span className="text-xs font-normal text-muted-foreground">/100</span></span>
                } />
                <InfoRow label="Created" value={
                  lead.created_at ? new Date(lead.created_at).toLocaleString() : '-'
                } />
                <InfoRow label="Last Active" value={
                  lead.updated_at ? new Date(lead.updated_at).toLocaleString() : '-'
                } />
              </div>
            </CardContent>
          </Card>

          {/* Status & notes editor */}
          <Card>
            <CardHeader>
              <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Update Lead</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Status</label>
                <div className="flex flex-wrap gap-2">
                  {statusOptions.map(s => (
                    <Button
                      key={s}
                      variant={status === s ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setStatus(s)}
                      className="text-xs"
                    >
                      {s}
                    </Button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Notes</label>
                <Textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  rows={4}
                  placeholder="Add notes about this lead..."
                  className="resize-none"
                />
              </div>

              <Button
                onClick={handleSave}
                disabled={saving}
                className="w-full"
              >
                {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</> : 'Save Changes'}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Conversation */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="border-b">
              <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Conversation ({lead.conversation?.length || 0} messages)
              </CardTitle>
            </CardHeader>
            <ChatViewer messages={lead.conversation || []} />
          </Card>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between items-start py-1.5 border-b border-border/50 last:border-0">
      <span className="text-xs text-muted-foreground font-medium">{label}</span>
      <span className="text-sm text-right max-w-[200px] break-words">
        {value || <span className="text-muted-foreground/50">-</span>}
      </span>
    </div>
  )
}
