import { useState, useEffect } from 'react'
import { getEmailSequences, getEmailSequence, createEmailSequence, addSequenceStep, getSequenceFunnel, getEmailTemplates } from '../../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Plus, GitBranch, Loader2, ArrowDown, Clock, Mail, ChevronRight, Save, X } from 'lucide-react'

const conditionLabels = {
  always: 'Always send',
  if_opened: 'If previous opened',
  if_not_opened: 'If previous NOT opened',
  if_clicked: 'If previous clicked',
  if_not_clicked: 'If previous NOT clicked',
}

function StepCard({ step, index, templates }) {
  const template = templates.find(t => t.id === step.template_id)
  return (
    <div className="relative">
      {index > 0 && (
        <div className="flex items-center justify-center py-2">
          <div className="flex flex-col items-center text-muted-foreground">
            <ArrowDown className="w-4 h-4" />
            <span className="text-[10px]">
              {step.delay_days > 0 && `${step.delay_days}d`}
              {step.delay_hours > 0 && ` ${step.delay_hours}h`}
              {!step.delay_days && !step.delay_hours && 'Immediate'}
            </span>
          </div>
        </div>
      )}
      <Card className="border-l-4 border-l-primary">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">
                {index + 1}
              </div>
              <div>
                <div className="font-semibold text-sm">{template?.name || `Template #${step.template_id}`}</div>
                <div className="text-xs text-muted-foreground">{template?.subject || 'No subject'}</div>
              </div>
            </div>
            <Badge variant="outline" className="text-[10px]">{conditionLabels[step.condition_type] || step.condition_type}</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function FunnelBar({ label, value, max }) {
  const pct = max > 0 ? (value / max * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-muted-foreground w-20 text-right">{label}</span>
      <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden">
        <div className="h-full bg-primary/70 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium w-10">{value}</span>
    </div>
  )
}

export default function EmailSequences() {
  const [sequences, setSequences] = useState([])
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null) // full sequence detail
  const [funnel, setFunnel] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showAddStep, setShowAddStep] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', description: '', campaign_type: 'warm', trigger_event: 'manual' })
  const [stepForm, setStepForm] = useState({ template_id: '', delay_days: 0, delay_hours: 0, condition_type: 'always' })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([
      getEmailSequences().then(d => setSequences(d.sequences || [])),
      getEmailTemplates().then(d => setTemplates(d.templates || [])),
    ]).finally(() => setLoading(false))
  }, [])

  async function selectSequence(id) {
    try {
      const [seq, f] = await Promise.all([getEmailSequence(id), getSequenceFunnel(id)])
      setSelected(seq)
      setFunnel(f)
    } catch (e) { console.error(e) }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setSaving(true)
    try {
      const result = await createEmailSequence(createForm)
      setShowCreate(false)
      setCreateForm({ name: '', description: '', campaign_type: 'warm', trigger_event: 'manual' })
      const d = await getEmailSequences()
      setSequences(d.sequences || [])
      await selectSequence(result.id)
    } catch (e) { alert(e.message) }
    finally { setSaving(false) }
  }

  async function handleAddStep(e) {
    e.preventDefault()
    if (!selected) return
    setSaving(true)
    try {
      await addSequenceStep(selected.id, { ...stepForm, template_id: Number(stepForm.template_id) })
      setShowAddStep(false)
      setStepForm({ template_id: '', delay_days: 0, delay_hours: 0, condition_type: 'always' })
      await selectSequence(selected.id)
    } catch (e) { alert(e.message) }
    finally { setSaving(false) }
  }

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Email Sequences</h1>
          <p className="text-sm text-muted-foreground">Automated drip campaigns and follow-up series</p>
        </div>
        <Button onClick={() => setShowCreate(true)}><Plus className="w-4 h-4 mr-2" />New Sequence</Button>
      </div>

      {/* Create form */}
      {showCreate && (
        <Card className="mb-4">
          <CardContent className="p-4">
            <form onSubmit={handleCreate} className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div><Label>Name</Label><Input value={createForm.name} onChange={e => setCreateForm(p => ({...p, name: e.target.value}))} required className="mt-1" /></div>
                <div>
                  <Label>Type</Label>
                  <select value={createForm.campaign_type} onChange={e => setCreateForm(p => ({...p, campaign_type: e.target.value}))} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                    <option value="warm">Warm</option><option value="cold">Cold</option>
                  </select>
                </div>
                <div>
                  <Label>Trigger</Label>
                  <select value={createForm.trigger_event} onChange={e => setCreateForm(p => ({...p, trigger_event: e.target.value}))} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                    <option value="manual">Manual</option><option value="lead_status_change">Lead Status Change</option><option value="score_threshold">Score Threshold</option>
                  </select>
                </div>
              </div>
              <div><Label>Description</Label><Input value={createForm.description} onChange={e => setCreateForm(p => ({...p, description: e.target.value}))} className="mt-1" /></div>
              <div className="flex gap-2">
                <Button type="submit" disabled={saving}>{saving ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Save className="w-4 h-4 mr-1" />}Create</Button>
                <Button type="button" variant="outline" onClick={() => setShowCreate(false)}><X className="w-4 h-4 mr-1" />Cancel</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sequence list */}
        <div className="space-y-2">
          {sequences.length === 0 ? (
            <Card><CardContent className="py-12 text-center text-muted-foreground">
              <GitBranch className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p>No sequences yet</p>
            </CardContent></Card>
          ) : sequences.map(s => (
            <Card
              key={s.id}
              className={`cursor-pointer transition-colors ${selected?.id === s.id ? 'border-primary' : 'hover:border-primary/30'}`}
              onClick={() => selectSequence(s.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-sm">{s.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant={s.campaign_type === 'warm' ? 'default' : 'secondary'} className="text-[10px]">{s.campaign_type}</Badge>
                      <span className="text-xs text-muted-foreground">{s.enrollment_count} enrolled</span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Sequence detail */}
        <div className="lg:col-span-2">
          {selected ? (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>{selected.name}</CardTitle>
                      <CardDescription>{selected.description || 'No description'}</CardDescription>
                    </div>
                    <Button size="sm" onClick={() => setShowAddStep(true)}><Plus className="w-3 h-3 mr-1" />Add Step</Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {/* Add step form */}
                  {showAddStep && (
                    <form onSubmit={handleAddStep} className="mb-6 p-4 bg-muted/50 rounded-lg space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label>Template</Label>
                          <select value={stepForm.template_id} onChange={e => setStepForm(p => ({...p, template_id: e.target.value}))} required className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                            <option value="">Select template...</option>
                            {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                          </select>
                        </div>
                        <div>
                          <Label>Condition</Label>
                          <select value={stepForm.condition_type} onChange={e => setStepForm(p => ({...p, condition_type: e.target.value}))} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                            {Object.entries(conditionLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                          </select>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div><Label>Delay Days</Label><Input type="number" min={0} value={stepForm.delay_days} onChange={e => setStepForm(p => ({...p, delay_days: Number(e.target.value)}))} className="mt-1" /></div>
                        <div><Label>Delay Hours</Label><Input type="number" min={0} value={stepForm.delay_hours} onChange={e => setStepForm(p => ({...p, delay_hours: Number(e.target.value)}))} className="mt-1" /></div>
                      </div>
                      <div className="flex gap-2">
                        <Button type="submit" size="sm" disabled={saving}>Add Step</Button>
                        <Button type="button" size="sm" variant="outline" onClick={() => setShowAddStep(false)}>Cancel</Button>
                      </div>
                    </form>
                  )}

                  {/* Steps */}
                  {(selected.steps || []).length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground text-sm">No steps yet. Add the first step above.</div>
                  ) : (
                    <div className="max-w-md mx-auto">
                      {selected.steps.map((step, i) => <StepCard key={step.id} step={step} index={i} templates={templates} />)}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Funnel */}
              {funnel && funnel.total_enrolled > 0 && (
                <Card>
                  <CardHeader><CardTitle>Enrollment Funnel</CardTitle></CardHeader>
                  <CardContent className="space-y-2">
                    <FunnelBar label="Enrolled" value={funnel.total_enrolled} max={funnel.total_enrolled} />
                    <FunnelBar label="Active" value={funnel.active} max={funnel.total_enrolled} />
                    <FunnelBar label="Completed" value={funnel.completed} max={funnel.total_enrolled} />
                    <FunnelBar label="Cancelled" value={funnel.cancelled} max={funnel.total_enrolled} />
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="py-16 text-center text-muted-foreground">
                <GitBranch className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>Select a sequence to view its steps and funnel</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
