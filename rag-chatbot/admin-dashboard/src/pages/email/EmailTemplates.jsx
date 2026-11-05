import { useState, useEffect } from 'react'
import { getEmailTemplates, createEmailTemplate, updateEmailTemplate, previewEmailTemplate, duplicateEmailTemplate, deleteEmailTemplate } from '../../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Plus, FileText, Loader2, Eye, Copy, Save, X, Trash2 } from 'lucide-react'

const categories = ['welcome', 'follow_up', 'promotion', 'newsletter', 'drip']

export default function EmailTemplates() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null) // template object or 'new'
  const [preview, setPreview] = useState(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ name: '', subject: '', html_body: '', text_body: '', category: 'promotion', variables: [] })

  useEffect(() => { loadTemplates() }, [])

  async function loadTemplates() {
    try {
      const d = await getEmailTemplates()
      setTemplates(d.templates || [])
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  function startCreate() {
    setForm({ name: '', subject: '', html_body: '', text_body: '', category: 'promotion', variables: [] })
    setEditing('new')
    setPreview(null)
  }

  function startEdit(t) {
    setForm({ name: t.name, subject: t.subject, html_body: t.html_body, text_body: t.text_body, category: t.category, variables: t.variables || [] })
    setEditing(t)
    setPreview(null)
  }

  async function handleSave() {
    setSaving(true)
    try {
      if (editing === 'new') {
        await createEmailTemplate(form)
      } else {
        await updateEmailTemplate(editing.id, form)
      }
      setEditing(null)
      await loadTemplates()
    } catch (e) { alert(e.message) }
    finally { setSaving(false) }
  }

  async function handlePreview() {
    if (editing === 'new') {
      setPreview({ html_body: form.html_body, subject: form.subject })
      return
    }
    try {
      const p = await previewEmailTemplate(editing.id)
      setPreview(p)
    } catch (e) { alert(e.message) }
  }

  async function handleDuplicate(id) {
    try {
      await duplicateEmailTemplate(id)
      await loadTemplates()
    } catch (e) { alert(e.message) }
  }

  async function handleDelete(id, name) {
    if (!confirm(`Delete template "${name}"? This cannot be undone.`)) return
    try {
      await deleteEmailTemplate(id)
      await loadTemplates()
    } catch (e) { alert(e.message) }
  }

  function insertVariable(varName) {
    setForm(prev => ({
      ...prev,
      html_body: prev.html_body + `{{${varName}}}`,
    }))
  }

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>

  // Editor view
  if (editing !== null) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold tracking-tight">{editing === 'new' ? 'New Template' : `Edit: ${editing.name}`}</h1>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handlePreview}><Eye className="w-4 h-4 mr-2" />Preview</Button>
            <Button variant="outline" onClick={() => { setEditing(null); setPreview(null) }}><X className="w-4 h-4 mr-2" />Cancel</Button>
            <Button onClick={handleSave} disabled={saving || !form.name}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}Save
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Editor */}
          <Card>
            <CardContent className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="name">Template Name</Label>
                  <Input id="name" value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="category">Category</Label>
                  <select
                    id="category" value={form.category}
                    onChange={e => setForm(p => ({...p, category: e.target.value}))}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    {categories.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <Label htmlFor="subject">Subject Line</Label>
                <Input id="subject" value={form.subject} onChange={e => setForm(p => ({...p, subject: e.target.value}))} className="mt-1" />
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label>HTML Body</Label>
                  <div className="flex gap-1">
                    {['name', 'first_name', 'company', 'email'].map(v => (
                      <button key={v} onClick={() => insertVariable(v)} className="text-[10px] px-2 py-0.5 rounded bg-muted hover:bg-muted-foreground/10">
                        {`{{${v}}}`}
                      </button>
                    ))}
                  </div>
                </div>
                <textarea
                  value={form.html_body}
                  onChange={e => setForm(p => ({...p, html_body: e.target.value}))}
                  className="w-full h-[300px] rounded-md border border-input bg-background px-3 py-2 text-sm font-mono resize-y"
                  placeholder="<h1>Hello {{name}}</h1><p>Your email content here...</p>"
                />
              </div>
              <div>
                <Label>Plain Text Body (optional fallback)</Label>
                <textarea
                  value={form.text_body}
                  onChange={e => setForm(p => ({...p, text_body: e.target.value}))}
                  className="w-full h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm font-mono resize-y mt-1"
                  placeholder="Hello {{name}}, ..."
                />
              </div>
            </CardContent>
          </Card>

          {/* Preview */}
          <Card>
            <CardHeader>
              <CardTitle>Preview</CardTitle>
              <CardDescription>{preview ? 'Rendered with sample data' : 'Click "Preview" to see rendered output'}</CardDescription>
            </CardHeader>
            <CardContent>
              {preview ? (
                <div className="border rounded-lg overflow-hidden">
                  <div className="bg-muted px-4 py-2 text-sm font-medium">Subject: {preview.subject}</div>
                  <iframe
                    srcDoc={preview.html_body}
                    className="w-full h-[400px] bg-white"
                    sandbox="allow-same-origin"
                    title="Email Preview"
                  />
                </div>
              ) : (
                <div className="border rounded-lg overflow-hidden">
                  <iframe
                    srcDoc={form.html_body || '<p style="color:#999;text-align:center;padding:40px;">Start typing to see preview...</p>'}
                    className="w-full h-[400px] bg-white"
                    sandbox="allow-same-origin"
                    title="Live Preview"
                  />
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // List view
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Email Templates</h1>
          <p className="text-sm text-muted-foreground">Create and manage reusable email templates</p>
        </div>
        <Button onClick={startCreate}><Plus className="w-4 h-4 mr-2" />New Template</Button>
      </div>

      {templates.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground/30" />
            <h3 className="font-semibold mb-1">No templates yet</h3>
            <p className="text-sm text-muted-foreground mb-4">Create your first email template to use in campaigns.</p>
            <Button onClick={startCreate}><Plus className="w-4 h-4 mr-2" />New Template</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map(t => (
            <Card key={t.id} className="cursor-pointer hover:border-primary/30 transition-colors" onClick={() => startEdit(t)}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-sm">{t.name}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">{t.subject || 'No subject'}</p>
                  </div>
                  <Badge variant="outline" className="text-[10px]">{t.category}</Badge>
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={e => { e.stopPropagation(); handleDuplicate(t.id) }}>
                    <Copy className="w-3 h-3 mr-1" />Duplicate
                  </Button>
                  <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive hover:text-destructive" onClick={e => { e.stopPropagation(); handleDelete(t.id, t.name) }}>
                    <Trash2 className="w-3 h-3 mr-1" />Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
