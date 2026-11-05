import { useState, useEffect } from 'react'
import { getGoldenQAList, createGoldenQA, updateGoldenQA, deleteGoldenQA, syncGoldenQA } from '../api'
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Plus, Save, X, RefreshCw, Trash2, Pencil, ToggleLeft, ToggleRight, Sparkles, Loader2 } from 'lucide-react'

export default function GoldenQA() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null) // null = list view, 'new' or id = editor
  const [form, setForm] = useState({ question: '', answer: '', category: '' })
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [filterCategory, setFilterCategory] = useState('')

  function loadItems() {
    setLoading(true)
    getGoldenQAList()
      .then(data => setItems(data.items || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadItems() }, [])

  const categories = [...new Set(items.map(i => i.category).filter(Boolean))]
  const filtered = filterCategory
    ? items.filter(i => i.category === filterCategory)
    : items

  function startNew() {
    setForm({ question: '', answer: '', category: '' })
    setEditing('new')
  }

  function startEdit(item) {
    setForm({ question: item.question, answer: item.answer, category: item.category || '' })
    setEditing(item.id)
  }

  function cancelEdit() {
    setEditing(null)
    setForm({ question: '', answer: '', category: '' })
  }

  async function handleSave() {
    if (!form.question.trim() || !form.answer.trim()) return
    setSaving(true)
    try {
      if (editing === 'new') {
        await createGoldenQA(form)
      } else {
        await updateGoldenQA(editing, form)
      }
      cancelEdit()
      loadItems()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this Q&A pair?')) return
    try {
      await deleteGoldenQA(id)
      loadItems()
    } catch (e) {
      console.error(e)
    }
  }

  async function handleToggle(item) {
    try {
      await updateGoldenQA(item.id, { is_active: item.is_active ? 0 : 1 })
      loadItems()
    } catch (e) {
      console.error(e)
    }
  }

  async function handleSync() {
    setSyncing(true)
    try {
      const result = await syncGoldenQA()
      alert(`Synced ${result.synced} Q&A pairs to knowledge base`)
    } catch (e) {
      console.error(e)
    } finally {
      setSyncing(false)
    }
  }

  // Editor view
  if (editing !== null) {
    return (
      <div>
        <div className="mb-6">
          <h1 className="text-2xl font-bold">
            {editing === 'new' ? 'Add Q&A Pair' : 'Edit Q&A Pair'}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Write the ideal question and answer for the chatbot
          </p>
        </div>

        <Card>
          <CardContent className="p-6 space-y-5">
            <div>
              <Label htmlFor="question">Question</Label>
              <Input
                id="question"
                value={form.question}
                onChange={e => setForm({ ...form, question: e.target.value })}
                placeholder="What question should trigger this answer?"
                className="mt-1.5"
              />
            </div>

            <div>
              <Label htmlFor="answer">Answer</Label>
              <Textarea
                id="answer"
                value={form.answer}
                onChange={e => setForm({ ...form, answer: e.target.value })}
                placeholder="Write the ideal response (supports markdown)..."
                rows={8}
                className="mt-1.5 resize-none"
              />
            </div>

            <div>
              <Label htmlFor="category">Category (optional)</Label>
              <Input
                id="category"
                value={form.category}
                onChange={e => setForm({ ...form, category: e.target.value })}
                placeholder="e.g. Services, Pricing, General"
                className="mt-1.5"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <Button onClick={handleSave} disabled={saving || !form.question.trim() || !form.answer.trim()}>
                {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</> : <><Save className="w-4 h-4 mr-2" />Save</>}
              </Button>
              <Button variant="outline" onClick={cancelEdit}>
                <X className="w-4 h-4 mr-2" />Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // List view
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Golden Q&A</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Curated ideal answers that take priority in chatbot responses
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleSync} disabled={syncing}>
            {syncing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            Sync All
          </Button>
          <Button onClick={startNew}>
            <Plus className="w-4 h-4 mr-2" />Add Q&A
          </Button>
        </div>
      </div>

      {/* Category filters */}
      {categories.length > 0 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          <Button
            variant={filterCategory === '' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterCategory('')}
            className="text-xs"
          >
            All
          </Button>
          {categories.map(cat => (
            <Button
              key={cat}
              variant={filterCategory === cat ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterCategory(cat)}
              className="text-xs"
            >
              {cat}
            </Button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center text-muted-foreground">
          <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" />
          Loading...
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <div className="py-20 text-center text-muted-foreground">
            <Sparkles className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm font-medium">No Q&A pairs yet</p>
            <p className="text-xs mt-1 mb-4">Add your first golden Q&A pair to train the chatbot</p>
            <Button onClick={startNew} size="sm">
              <Plus className="w-4 h-4 mr-2" />Add Q&A Pair
            </Button>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map(item => (
            <Card key={item.id} className={!item.is_active ? 'opacity-50' : ''}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      {item.category && (
                        <Badge variant="outline" className="text-[10px]">{item.category}</Badge>
                      )}
                      <Badge variant={item.is_active ? 'default' : 'secondary'} className="text-[10px]">
                        {item.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <p className="text-sm font-medium mb-1.5">{item.question}</p>
                    <p className="text-xs text-muted-foreground whitespace-pre-wrap line-clamp-3">
                      {item.answer}
                    </p>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button variant="ghost" size="sm" onClick={() => handleToggle(item)} title={item.is_active ? 'Deactivate' : 'Activate'}>
                      {item.is_active ? <ToggleRight className="w-4 h-4" /> : <ToggleLeft className="w-4 h-4" />}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => startEdit(item)}>
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(item.id)} className="text-destructive hover:text-destructive">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
