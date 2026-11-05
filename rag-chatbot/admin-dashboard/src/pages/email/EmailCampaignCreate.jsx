import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { createEmailCampaign, getEmailTemplates, getLeads, getEmailContacts } from '../../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowLeft, ArrowRight, Send, Check, Loader2 } from 'lucide-react'

const steps = ['Type & Name', 'Template', 'Recipients', 'Subject & A/B', 'Review']

export default function EmailCampaignCreate() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [saving, setSaving] = useState(false)
  const [templates, setTemplates] = useState([])
  const [form, setForm] = useState({
    name: '',
    campaign_type: 'warm',
    template_id: null,
    subject_line: '',
    from_name: '',
    from_email: '',
    reply_to: '',
    target_filter: {},
    ab_enabled: false,
    ab_variant_b_subject: '',
  })

  // Filter state for warm campaigns
  const [warmSource, setWarmSource] = useState('leads') // 'leads' or 'custom'
  const [leadStatuses, setLeadStatuses] = useState(['hot', 'qualified'])
  const [minScore, setMinScore] = useState(0)
  const [customEmails, setCustomEmails] = useState('') // one per line: email, name

  // Cold filter state
  const [contactTags, setContactTags] = useState('')

  useEffect(() => {
    getEmailTemplates().then(d => setTemplates(d.templates || [])).catch(console.error)
  }, [])

  function updateForm(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  async function handleCreate() {
    setSaving(true)
    try {
      let targetFilter
      if (form.campaign_type === 'warm') {
        if (warmSource === 'custom') {
          const parsed = customEmails.split('\n').filter(l => l.trim()).map(line => {
            const parts = line.split(',').map(p => p.trim())
            return { email: parts[0] || '', name: parts[1] || '', company: parts[2] || '' }
          }).filter(e => e.email)
          targetFilter = { recipient_source: 'custom', custom_emails: parsed }
        } else {
          targetFilter = { recipient_source: 'leads', status: leadStatuses, min_score: minScore || undefined }
        }
      } else {
        targetFilter = { tags: contactTags ? contactTags.split(',').map(t => t.trim()) : [] }
      }

      const payload = { ...form, target_filter: targetFilter }
      const result = await createEmailCampaign(payload)
      navigate(`/email/${result.id}`)
    } catch (e) {
      alert('Error creating campaign: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  const canProceed = () => {
    if (step === 0) return form.name.trim() !== ''
    if (step === 1) return form.template_id !== null
    if (step === 3) return form.subject_line.trim() !== ''
    return true
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" size="icon" onClick={() => navigate('/email')}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Create Campaign</h1>
          <p className="text-sm text-muted-foreground">Step {step + 1} of {steps.length}: {steps[step]}</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="flex gap-1 mb-8">
        {steps.map((s, i) => (
          <div key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? 'bg-primary' : 'bg-muted'}`} />
        ))}
      </div>

      <Card className="max-w-2xl">
        <CardContent className="p-6">
          {/* Step 0: Type & Name */}
          {step === 0 && (
            <div className="space-y-5">
              <div>
                <Label className="text-sm font-medium mb-2 block">Campaign Type</Label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { value: 'warm', label: 'Warm', desc: 'Existing leads from your chatbot' },
                    { value: 'cold', label: 'Cold', desc: 'New prospects from imported lists' },
                  ].map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => updateForm('campaign_type', opt.value)}
                      className={`p-4 rounded-lg border-2 text-left transition-colors ${
                        form.campaign_type === opt.value ? 'border-primary bg-primary/5' : 'border-muted hover:border-muted-foreground/20'
                      }`}
                    >
                      <div className="font-semibold text-sm">{opt.label}</div>
                      <div className="text-xs text-muted-foreground mt-1">{opt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <Label htmlFor="name">Campaign Name</Label>
                <Input id="name" value={form.name} onChange={e => updateForm('name', e.target.value)} placeholder="e.g., February Newsletter" className="mt-1" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="from_name">From Name</Label>
                  <Input id="from_name" value={form.from_name} onChange={e => updateForm('from_name', e.target.value)} placeholder="Sparrowi" className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="from_email">From Email</Label>
                  <Input id="from_email" value={form.from_email} onChange={e => updateForm('from_email', e.target.value)} placeholder="hello@sparrowi.com" className="mt-1" />
                </div>
              </div>
            </div>
          )}

          {/* Step 1: Template */}
          {step === 1 && (
            <div>
              <Label className="text-sm font-medium mb-3 block">Select a Template</Label>
              {templates.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No templates yet. Create one in the Templates page first.</p>
                  <Button variant="outline" className="mt-3" onClick={() => navigate('/email/templates')}>Go to Templates</Button>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 max-h-[400px] overflow-y-auto">
                  {templates.map(t => (
                    <button
                      key={t.id}
                      onClick={() => updateForm('template_id', t.id)}
                      className={`p-4 rounded-lg border-2 text-left transition-colors ${
                        form.template_id === t.id ? 'border-primary bg-primary/5' : 'border-muted hover:border-muted-foreground/20'
                      }`}
                    >
                      <div className="font-semibold text-sm">{t.name}</div>
                      <div className="text-xs text-muted-foreground mt-1">{t.category} &middot; {t.subject || 'No subject'}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 2: Recipients */}
          {step === 2 && (
            <div className="space-y-4">
              {form.campaign_type === 'warm' ? (
                <>
                  <Label className="text-sm font-medium mb-2 block">Recipient Source</Label>
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    {[
                      { value: 'leads', label: 'Existing Leads', desc: 'Send to leads captured by your chatbot' },
                      { value: 'custom', label: 'Custom Emails', desc: 'Enter your own email list (previous clients, etc.)' },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        onClick={() => setWarmSource(opt.value)}
                        className={`p-4 rounded-lg border-2 text-left transition-colors ${
                          warmSource === opt.value ? 'border-primary bg-primary/5' : 'border-muted hover:border-muted-foreground/20'
                        }`}
                      >
                        <div className="font-semibold text-sm">{opt.label}</div>
                        <div className="text-xs text-muted-foreground mt-1">{opt.desc}</div>
                      </button>
                    ))}
                  </div>

                  {warmSource === 'leads' ? (
                    <>
                      <Label className="text-sm font-medium mb-2 block">Target Lead Statuses</Label>
                      <div className="flex flex-wrap gap-2">
                        {['new', 'engaged', 'qualified', 'hot', 'converted'].map(s => (
                          <button
                            key={s}
                            onClick={() => setLeadStatuses(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])}
                            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                              leadStatuses.includes(s) ? 'bg-primary text-primary-foreground border-primary' : 'bg-muted border-muted'
                            }`}
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                      <div>
                        <Label htmlFor="minScore">Minimum Lead Score</Label>
                        <Input id="minScore" type="number" min={0} max={100} value={minScore} onChange={e => setMinScore(Number(e.target.value))} className="mt-1 w-32" />
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <Label htmlFor="customEmails">Email List</Label>
                        <textarea
                          id="customEmails"
                          value={customEmails}
                          onChange={e => setCustomEmails(e.target.value)}
                          placeholder={"john@example.com, John Doe, Acme Corp\njane@example.com, Jane Smith\nmark@company.com"}
                          rows={8}
                          className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring font-mono"
                        />
                        <p className="text-xs text-muted-foreground mt-1">One email per line. Format: <span className="font-mono">email, name, company</span> (name &amp; company are optional)</p>
                        <p className="text-xs text-muted-foreground">
                          {customEmails.split('\n').filter(l => l.trim() && l.trim().includes('@')).length} email(s) entered
                        </p>
                      </div>
                    </>
                  )}
                </>
              ) : (
                <>
                  <div>
                    <Label htmlFor="tags">Contact Tags (comma-separated)</Label>
                    <Input id="tags" value={contactTags} onChange={e => setContactTags(e.target.value)} placeholder="e.g., real-estate, mumbai" className="mt-1" />
                    <p className="text-xs text-muted-foreground mt-1">Leave empty to target all active contacts</p>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Step 3: Subject & A/B */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <Label htmlFor="subject">Subject Line</Label>
                <Input id="subject" value={form.subject_line} onChange={e => updateForm('subject_line', e.target.value)} placeholder="Your subject line..." className="mt-1" />
              </div>
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={() => updateForm('ab_enabled', !form.ab_enabled)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${form.ab_enabled ? 'bg-primary' : 'bg-muted'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.ab_enabled ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
                <Label>Enable A/B Testing</Label>
              </div>
              {form.ab_enabled && (
                <div className="pl-4 border-l-2 border-primary/20 space-y-3">
                  <div>
                    <Label htmlFor="ab_subject">Variant B Subject Line</Label>
                    <Input id="ab_subject" value={form.ab_variant_b_subject} onChange={e => updateForm('ab_variant_b_subject', e.target.value)} placeholder="Alternate subject..." className="mt-1" />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Review */}
          {step === 4 && (
            <div className="space-y-4">
              <h3 className="font-semibold">Review Your Campaign</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between py-2 border-b"><span className="text-muted-foreground">Name</span><span className="font-medium">{form.name}</span></div>
                <div className="flex justify-between py-2 border-b"><span className="text-muted-foreground">Type</span><span className="font-medium capitalize">{form.campaign_type}</span></div>
                <div className="flex justify-between py-2 border-b"><span className="text-muted-foreground">Template</span><span className="font-medium">{templates.find(t => t.id === form.template_id)?.name || 'None'}</span></div>
                <div className="flex justify-between py-2 border-b"><span className="text-muted-foreground">Subject</span><span className="font-medium">{form.subject_line}</span></div>
                <div className="flex justify-between py-2 border-b"><span className="text-muted-foreground">A/B Testing</span><span className="font-medium">{form.ab_enabled ? 'Enabled' : 'Disabled'}</span></div>
                {form.campaign_type === 'warm' && warmSource === 'leads' && (
                  <div className="flex justify-between py-2 border-b"><span className="text-muted-foreground">Target</span><span className="font-medium">Existing Leads: {leadStatuses.join(', ')} (score &ge; {minScore})</span></div>
                )}
                {form.campaign_type === 'warm' && warmSource === 'custom' && (
                  <div className="flex justify-between py-2 border-b"><span className="text-muted-foreground">Target</span><span className="font-medium">Custom Emails: {customEmails.split('\n').filter(l => l.trim() && l.trim().includes('@')).length} recipient(s)</span></div>
                )}
                {form.campaign_type === 'cold' && contactTags && (
                  <div className="flex justify-between py-2 border-b"><span className="text-muted-foreground">Tags</span><span className="font-medium">{contactTags}</span></div>
                )}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-4 border-t">
            <Button variant="outline" onClick={() => step > 0 ? setStep(step - 1) : navigate('/email')} disabled={saving}>
              <ArrowLeft className="w-4 h-4 mr-2" /> {step === 0 ? 'Cancel' : 'Back'}
            </Button>
            {step < steps.length - 1 ? (
              <Button onClick={() => setStep(step + 1)} disabled={!canProceed()}>
                Next <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button onClick={handleCreate} disabled={saving}>
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
                Create Campaign
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
