import { useState, useEffect } from 'react'
import { getIssues, getIssue, updateIssue, deleteIssue } from '../api'
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { AlertTriangle, CheckCircle, Loader2, Trash2 } from 'lucide-react'

const STATUS_OPTIONS = ['open', 'investigating', 'resolved']

const statusVariantMap = {
  open: 'destructive',
  investigating: 'outline',
  resolved: 'secondary',
}

export default function Issues() {
  const [data, setData] = useState({ total: 0, issues: [] })
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [offset, setOffset] = useState(0)
  const [filterStatus, setFilterStatus] = useState('')
  const [editNotes, setEditNotes] = useState('')
  const [editStatus, setEditStatus] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const limit = 30

  function loadIssues() {
    setLoading(true)
    getIssues({ limit, offset, status: filterStatus })
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadIssues()
  }, [offset, filterStatus])

  async function selectIssue(id) {
    setSelected(id)
    setLoadingDetail(true)
    try {
      const result = await getIssue(id)
      setDetail(result)
      setEditStatus(result.status)
      setEditNotes(result.admin_notes || '')
    } catch (e) {
      console.error(e)
      setDetail(null)
    } finally {
      setLoadingDetail(false)
    }
  }

  async function handleSave() {
    if (!detail) return
    setSaving(true)
    try {
      await updateIssue(detail.id, {
        status: editStatus,
        admin_notes: editNotes,
      })
      const updated = await getIssue(detail.id)
      setDetail(updated)
      loadIssues()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!detail || !window.confirm('Are you sure you want to delete this issue? This cannot be undone.')) return
    setDeleting(true)
    try {
      await deleteIssue(detail.id)
      setSelected(null)
      setDetail(null)
      loadIssues()
    } catch (e) {
      console.error(e)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Reported Issues</h1>
        <p className="text-sm text-muted-foreground mt-1">User-reported issues from the chatbot widget</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Issue list */}
        <div className="lg:col-span-1">
          <Card className="overflow-hidden">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{data.total} issues</p>
              <select
                value={filterStatus}
                onChange={e => { setFilterStatus(e.target.value); setOffset(0) }}
                className="text-xs border border-input rounded-md px-2 py-1 bg-transparent focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="">All statuses</option>
                {STATUS_OPTIONS.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <ScrollArea className="h-[600px]">
              {loading ? (
                <div className="px-4 py-12 text-center text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                  Loading...
                </div>
              ) : data.issues.length === 0 ? (
                <div className="px-4 py-12 text-center text-muted-foreground">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-40" />
                  No issues found
                </div>
              ) : (
                data.issues.map(issue => (
                  <button
                    key={issue.id}
                    onClick={() => selectIssue(issue.id)}
                    className={`w-full text-left px-4 py-3.5 border-b border-border/50 hover:bg-muted/50 transition-colors ${
                      selected === issue.id ? 'bg-muted border-l-2 border-l-primary' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">
                        #{issue.id}
                      </span>
                      <Badge variant={statusVariantMap[issue.status] || 'secondary'} className="text-[10px]">
                        {issue.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{issue.message}</p>
                    <p className="text-[11px] text-muted-foreground/50 mt-1">
                      {issue.created_at ? new Date(issue.created_at + 'Z').toLocaleString() : ''}
                    </p>
                  </button>
                ))
              )}
            </ScrollArea>
            {/* Pagination */}
            {data.total > limit && (
              <div className="flex justify-between px-4 py-2.5 border-t">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  className="text-xs"
                >
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={offset + limit >= data.total}
                  onClick={() => setOffset(offset + limit)}
                  className="text-xs"
                >
                  Next
                </Button>
              </div>
            )}
          </Card>
        </div>

        {/* Issue detail */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="border-b">
              <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {detail ? `Issue #${detail.id}` : 'Select an issue'}
              </CardTitle>
            </CardHeader>
            {!selected ? (
              <div className="py-20 text-center text-muted-foreground">
                <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-30" />
                Click an issue on the left to view details
              </div>
            ) : loadingDetail ? (
              <div className="py-20 text-center text-muted-foreground">
                <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" />
                Loading...
              </div>
            ) : detail ? (
              <CardContent className="p-6 space-y-5">
                <div>
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Description</label>
                  <p className="mt-2 text-sm whitespace-pre-wrap bg-muted rounded-lg p-4 border leading-relaxed">
                    {detail.message}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <InfoRow label="Session ID" value={<span className="font-mono text-[12px]">{detail.session_id}</span>} />
                  <InfoRow label="Page URL" value={detail.page_url || '\u2014'} />
                  <InfoRow label="Reported At" value={detail.created_at ? new Date(detail.created_at + 'Z').toLocaleString() : '\u2014'} />
                  <InfoRow label="Last Updated" value={detail.updated_at ? new Date(detail.updated_at + 'Z').toLocaleString() : '\u2014'} />
                </div>

                <Separator />

                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Status</label>
                  <div className="flex gap-2">
                    {STATUS_OPTIONS.map(s => (
                      <Button
                        key={s}
                        variant={editStatus === s ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setEditStatus(s)}
                        className="text-xs"
                      >
                        {s}
                      </Button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Admin Notes</label>
                  <Textarea
                    value={editNotes}
                    onChange={e => setEditNotes(e.target.value)}
                    rows={3}
                    placeholder="Add internal notes about this issue..."
                    className="resize-none"
                  />
                </div>

                <div className="flex gap-3">
                  <Button
                    onClick={handleSave}
                    disabled={saving}
                  >
                    {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</> : 'Save Changes'}
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleDelete}
                    disabled={deleting}
                  >
                    {deleting ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Deleting...</> : <><Trash2 className="w-4 h-4 mr-2" />Delete</>}
                  </Button>
                </div>
              </CardContent>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="py-2 border-b border-border/50">
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{label}</label>
      <p className="mt-1 text-xs">{value}</p>
    </div>
  )
}
