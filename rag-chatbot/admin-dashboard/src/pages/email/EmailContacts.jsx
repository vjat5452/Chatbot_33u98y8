import { useState, useEffect, useRef } from 'react'
import { getEmailContacts, createEmailContact, importEmailContacts, syncLeadsToContacts, validateEmailContacts, getContactsExportUrl, deleteEmailContacts } from '../../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Plus, Upload, Download, RefreshCw, Search, Loader2, Users2, CheckCircle, XCircle, Shield, Trash2 } from 'lucide-react'

const statusColors = {
  active: 'bg-emerald-100 text-emerald-700',
  unsubscribed: 'bg-gray-100 text-gray-700',
  bounced: 'bg-red-100 text-red-700',
  cleaned: 'bg-yellow-100 text-yellow-700',
}

export default function EmailContacts() {
  const [contacts, setContacts] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ email: '', name: '', company: '', phone: '', tags: '' })
  const [importing, setImporting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState(null)
  const [importResult, setImportResult] = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [deleting, setDeleting] = useState(false)
  const fileRef = useRef(null)
  const limit = 50

  useEffect(() => { loadContacts() }, [page, statusFilter])

  async function loadContacts() {
    setLoading(true)
    try {
      const d = await getEmailContacts({ status: statusFilter || undefined, search: search || undefined, limit, offset: page * limit })
      setContacts(d.contacts || [])
      setTotal(d.total || 0)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  function handleSearch(e) {
    e.preventDefault()
    setPage(0)
    loadContacts()
  }

  async function handleAdd(e) {
    e.preventDefault()
    try {
      await createEmailContact(addForm)
      setShowAdd(false)
      setAddForm({ email: '', name: '', company: '', phone: '', tags: '' })
      loadContacts()
    } catch (e) { alert(e.message) }
  }

  async function handleImport(e) {
    const file = e.target.files[0]
    if (!file) return
    setImporting(true)
    setImportResult(null)
    try {
      const result = await importEmailContacts(file)
      setImportResult(result)
      loadContacts()
    } catch (e) { alert(e.message) }
    finally { setImporting(false); if (fileRef.current) fileRef.current.value = '' }
  }

  async function handleSync() {
    setSyncing(true)
    try {
      const result = await syncLeadsToContacts()
      alert(`Synced ${result.synced} leads, ${result.skipped} skipped`)
      loadContacts()
    } catch (e) { alert(e.message) }
    finally { setSyncing(false) }
  }

  function toggleSelect(id) {
    setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s })
  }

  function toggleAll() {
    if (selected.size === contacts.length) setSelected(new Set())
    else setSelected(new Set(contacts.map(c => c.id)))
  }

  async function handleDelete() {
    if (selected.size === 0) return
    if (!confirm(`Delete ${selected.size} contact(s)? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await deleteEmailContacts([...selected])
      setSelected(new Set())
      loadContacts()
    } catch (e) { alert(e.message) }
    finally { setDeleting(false) }
  }

  async function handleValidate() {
    setValidating(true)
    try {
      const result = await validateEmailContacts()
      setValidationResult(result)
      loadContacts()
    } catch (e) { alert(e.message) }
    finally { setValidating(false) }
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Email Contacts</h1>
          <p className="text-sm text-muted-foreground">{total} contacts total</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleSync} disabled={syncing}>
            {syncing ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <RefreshCw className="w-3 h-3 mr-1" />} Sync Leads
          </Button>
          <Button variant="outline" size="sm" onClick={handleValidate} disabled={validating}>
            {validating ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Shield className="w-3 h-3 mr-1" />} Validate
          </Button>
          <a href={getContactsExportUrl(statusFilter)} download>
            <Button variant="outline" size="sm"><Download className="w-3 h-3 mr-1" /> Export</Button>
          </a>
          <div className="relative">
            <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={importing}>
              {importing ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Upload className="w-3 h-3 mr-1" />} Import CSV
            </Button>
            <input ref={fileRef} type="file" accept=".csv" onChange={handleImport} className="hidden" />
          </div>
          {selected.size > 0 && (
            <Button size="sm" variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Trash2 className="w-3 h-3 mr-1" />} Delete ({selected.size})
            </Button>
          )}
          <Button size="sm" onClick={() => setShowAdd(!showAdd)}>
            <Plus className="w-3 h-3 mr-1" /> Add
          </Button>
        </div>
      </div>

      {/* Import result banner */}
      {importResult && (
        <Card className="mb-4 border-blue-200 bg-blue-50">
          <CardContent className="py-3 px-4 flex items-center justify-between">
            <div className="text-sm">
              Imported: <strong>{importResult.created}</strong> created, <strong>{importResult.skipped}</strong> skipped
              {importResult.errors?.length > 0 && `, ${importResult.errors.length} errors`}
            </div>
            <Button variant="ghost" size="sm" onClick={() => setImportResult(null)}><XCircle className="w-4 h-4" /></Button>
          </CardContent>
        </Card>
      )}

      {/* Validation result */}
      {validationResult && (
        <Card className="mb-4 border-emerald-200 bg-emerald-50">
          <CardContent className="py-3 px-4 flex items-center justify-between">
            <div className="text-sm flex items-center gap-4">
              <span><CheckCircle className="w-4 h-4 inline mr-1 text-emerald-600" /><strong>{validationResult.valid}</strong> valid</span>
              <span><XCircle className="w-4 h-4 inline mr-1 text-red-600" /><strong>{validationResult.invalid}</strong> invalid</span>
              <span>{validationResult.disposable} disposable</span>
              <span>{validationResult.role_based} role-based</span>
              <span>{validationResult.no_mx} no MX</span>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setValidationResult(null)}><XCircle className="w-4 h-4" /></Button>
          </CardContent>
        </Card>
      )}

      {/* Add contact form */}
      {showAdd && (
        <Card className="mb-4">
          <CardContent className="p-4">
            <form onSubmit={handleAdd} className="flex items-end gap-3">
              <div className="flex-1"><Label>Email *</Label><Input value={addForm.email} onChange={e => setAddForm(p => ({...p, email: e.target.value}))} required className="mt-1" /></div>
              <div className="flex-1"><Label>Name</Label><Input value={addForm.name} onChange={e => setAddForm(p => ({...p, name: e.target.value}))} className="mt-1" /></div>
              <div className="flex-1"><Label>Company</Label><Input value={addForm.company} onChange={e => setAddForm(p => ({...p, company: e.target.value}))} className="mt-1" /></div>
              <div className="w-32"><Label>Tags</Label><Input value={addForm.tags} onChange={e => setAddForm(p => ({...p, tags: e.target.value}))} placeholder="tag1,tag2" className="mt-1" /></div>
              <Button type="submit">Add</Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search contacts..." className="w-64" />
          <Button variant="outline" type="submit"><Search className="w-4 h-4" /></Button>
        </form>
        <Tabs value={statusFilter} onValueChange={v => { setStatusFilter(v === 'all' ? '' : v); setPage(0) }}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="unsubscribed">Unsubscribed</TabsTrigger>
            <TabsTrigger value="bounced">Bounced</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
          ) : contacts.length === 0 ? (
            <div className="py-16 text-center text-muted-foreground">
              <Users2 className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p>No contacts found</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10"><input type="checkbox" checked={contacts.length > 0 && selected.size === contacts.length} onChange={toggleAll} className="rounded" /></TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contacts.map(c => (
                  <TableRow key={c.id}>
                    <TableCell><input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleSelect(c.id)} className="rounded" /></TableCell>
                    <TableCell className="font-medium text-sm">{c.email}</TableCell>
                    <TableCell className="text-sm">{c.name || '-'}</TableCell>
                    <TableCell className="text-sm">{c.company || '-'}</TableCell>
                    <TableCell>
                      {c.tags ? c.tags.split(',').map(t => (
                        <Badge key={t} variant="outline" className="text-[10px] mr-1">{t.trim()}</Badge>
                      )) : '-'}
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[c.status] || 'bg-gray-100 text-gray-700'}`}>
                        {c.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{c.source}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t">
            <div className="text-xs text-muted-foreground">Page {page + 1} of {totalPages}</div>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>Prev</Button>
              <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages - 1}>Next</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
