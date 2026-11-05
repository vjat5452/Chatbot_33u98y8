import { useState, useEffect, useCallback } from 'react'
import { Database, Upload, RefreshCw, Trash2, Eye, FileText, Globe, HardDrive, X, ChevronDown, ChevronUp } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

function authHeaders(extra = {}) {
  const token = sessionStorage.getItem('admin_token')
  const h = { ...extra }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

export default function Data() {
  const [sources, setSources] = useState(null)
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [viewChunks, setViewChunks] = useState(null)
  const [chunks, setChunks] = useState([])
  const [chunksLoading, setChunksLoading] = useState(false)
  const [expandedChunk, setExpandedChunk] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const fetchData = useCallback(async () => {
    try {
      const [srcRes, fileRes] = await Promise.all([
        fetch(`${API}/api/admin/data/sources`, { headers: authHeaders() }),
        fetch(`${API}/api/admin/data/files`, { headers: authHeaders() }),
      ])
      const srcData = await srcRes.json()
      const fileData = await fileRes.json()
      setSources(srcData)
      setFiles(fileData.files || [])
    } catch (err) {
      console.error('Failed to fetch data:', err)
      showToast('Failed to load data', 'error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleUpload = async (e) => {
    const selectedFiles = e.target.files
    if (!selectedFiles || selectedFiles.length === 0) return

    setUploading(true)
    const formData = new FormData()
    for (const file of selectedFiles) {
      formData.append('files', file)
    }

    try {
      const res = await fetch(`${API}/api/admin/data/upload`, {
        method: 'POST',
        headers: authHeaders(),
        body: formData,
      })
      const data = await res.json()

      if (!res.ok) {
        showToast(data.detail || 'Upload failed', 'error')
        return
      }

      const successCount = data.files.filter(f => !f.error).length
      const errorCount = data.files.filter(f => f.error).length

      if (successCount > 0 && errorCount === 0) {
        showToast(`Uploaded ${successCount} file(s) — ${data.total_chunks} chunks created`)
      } else if (successCount > 0 && errorCount > 0) {
        showToast(`${successCount} uploaded, ${errorCount} failed`, 'warning')
      } else {
        const firstError = data.files.find(f => f.error)
        showToast(firstError?.error || 'All files failed', 'error')
      }

      await fetchData()
    } catch (err) {
      showToast('Upload failed: ' + err.message, 'error')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleDelete = async (fileId, filename) => {
    if (!confirm(`Delete "${filename}" and all its chunks from the chatbot knowledge base?`)) return

    setDeleting(fileId)
    try {
      const res = await fetch(`${API}/api/admin/data/files/${fileId}`, { method: 'DELETE', headers: authHeaders() })
      const data = await res.json()
      if (res.ok) {
        showToast(data.message || `Deleted ${filename}`)
        if (viewChunks === fileId) {
          setViewChunks(null)
          setChunks([])
        }
        await fetchData()
      } else {
        showToast(data.detail || 'Delete failed', 'error')
      }
    } catch (err) {
      showToast('Delete failed: ' + err.message, 'error')
    } finally {
      setDeleting(null)
    }
  }

  const handleViewChunks = async (fileId) => {
    if (viewChunks === fileId) {
      setViewChunks(null)
      setChunks([])
      return
    }
    setViewChunks(fileId)
    setChunksLoading(true)
    setExpandedChunk(null)
    try {
      const res = await fetch(`${API}/api/admin/data/files/${fileId}/chunks`, { headers: authHeaders() })
      const data = await res.json()
      setChunks(data.chunks || [])
    } catch (err) {
      showToast('Failed to load chunks', 'error')
      setChunks([])
    } finally {
      setChunksLoading(false)
    }
  }

  const handleRefreshWebsite = async () => {
    setRefreshing(true)
    try {
      const res = await fetch(`${API}/api/admin/data/refresh-website`, { method: 'POST', headers: authHeaders() })
      const data = await res.json()
      if (data.status === 'ok') {
        showToast(data.message || 'Website data refreshed')
        await fetchData()
      } else {
        showToast(data.message || 'Refresh failed', 'error')
      }
    } catch (err) {
      showToast('Refresh failed: ' + err.message, 'error')
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" />
        Loading knowledge base...
      </div>
    )
  }

  const sourceIcons = {
    website: Globe,
    uploaded: HardDrive,
    golden_qa: FileText,
  }

  const sourceColors = {
    website: 'bg-blue-500/10 text-blue-600 border-blue-200',
    uploaded: 'bg-purple-500/10 text-purple-600 border-purple-200',
    golden_qa: 'bg-amber-500/10 text-amber-600 border-amber-200',
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all ${
          toast.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' :
          toast.type === 'warning' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
          'bg-green-50 text-green-700 border border-green-200'
        }`}>
          {toast.message}
          <button onClick={() => setToast(null)} className="ml-2 hover:opacity-70">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Knowledge Base</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage the data sources that power the chatbot's responses
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefreshWebsite}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-border hover:bg-accent transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh Website'}
          </button>
          <label className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg text-white cursor-pointer transition-colors ${
            uploading ? 'bg-primary/60 cursor-wait' : 'bg-primary hover:bg-primary/90'
          }`}>
            <input
              type="file"
              accept=".pdf,.sql"
              multiple
              hidden
              onChange={handleUpload}
              disabled={uploading}
            />
            <Upload className={`w-4 h-4 ${uploading ? 'animate-pulse' : ''}`} />
            {uploading ? 'Uploading...' : 'Upload Files'}
          </label>
        </div>
      </div>

      {/* Knowledge Sources Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {sources?.sources?.map((source) => {
          const Icon = sourceIcons[source.type] || Database
          const color = sourceColors[source.type] || 'bg-gray-100 text-gray-600'
          return (
            <div key={source.type} className={`rounded-xl border p-5 ${color}`}>
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-white/60">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm">{source.name}</h3>
                  <span className="text-[11px] uppercase tracking-wider opacity-70">{source.status}</span>
                </div>
              </div>
              <div className="text-3xl font-bold mb-1">{source.chunks}</div>
              <p className="text-xs opacity-70">{source.description}</p>
              {source.file_count !== undefined && (
                <p className="text-xs opacity-70 mt-1">{source.file_count} file(s)</p>
              )}
            </div>
          )
        })}
      </div>

      {/* Total chunks bar */}
      {sources && (
        <div className="bg-card border rounded-lg px-4 py-3 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Total knowledge chunks in Qdrant</span>
          <span className="font-bold text-lg">{sources.total_chunks}</span>
        </div>
      )}

      {/* Uploaded Files Section */}
      <div className="bg-card border rounded-xl">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-purple-600" />
            <h2 className="font-semibold">Uploaded Files</h2>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
              {files.length}
            </span>
          </div>
        </div>

        {files.length === 0 ? (
          <div className="px-5 py-12 text-center text-muted-foreground">
            <Upload className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="font-medium">No files uploaded yet</p>
            <p className="text-sm mt-1">Upload PDF or SQL files to add knowledge to the chatbot</p>
          </div>
        ) : (
          <div className="divide-y">
            {files.map((file) => (
              <div key={file.id}>
                <div className="px-5 py-3 flex items-center justify-between hover:bg-accent/30 transition-colors">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className={`p-2 rounded-lg ${
                      file.file_type === 'pdf' ? 'bg-red-50 text-red-500' : 'bg-blue-50 text-blue-500'
                    }`}>
                      <FileText className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{file.filename}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                        <span className="uppercase font-medium">{file.file_type}</span>
                        {file.total_pages > 0 && <span>{file.total_pages} pages</span>}
                        <span>{file.total_chunks} chunks</span>
                        <span>{formatBytes(file.file_size)}</span>
                        <span>{formatDate(file.uploaded_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 ml-4">
                    <button
                      onClick={() => handleViewChunks(file.id)}
                      className="p-2 rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                      title="View chunks"
                    >
                      {viewChunks === file.id ? <ChevronUp className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => handleDelete(file.id, file.filename)}
                      disabled={deleting === file.id}
                      className="p-2 rounded-lg text-muted-foreground hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-50"
                      title="Delete file and chunks"
                    >
                      <Trash2 className={`w-4 h-4 ${deleting === file.id ? 'animate-pulse' : ''}`} />
                    </button>
                  </div>
                </div>

                {/* Expanded chunks view */}
                {viewChunks === file.id && (
                  <div className="px-5 py-3 bg-muted/30 border-t">
                    {chunksLoading ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground py-4 justify-center">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Loading chunks...
                      </div>
                    ) : chunks.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4 text-center">No chunks found</p>
                    ) : (
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        <p className="text-xs text-muted-foreground mb-2">{chunks.length} chunks</p>
                        {chunks.map((chunk, idx) => (
                          <div
                            key={chunk.id || idx}
                            className="bg-card border rounded-lg p-3 text-sm cursor-pointer hover:border-primary/30 transition-colors"
                            onClick={() => setExpandedChunk(expandedChunk === idx ? null : idx)}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[11px] font-medium text-muted-foreground uppercase">
                                {chunk.chunk_type}
                              </span>
                              <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${
                                expandedChunk === idx ? 'rotate-180' : ''
                              }`} />
                            </div>
                            <p className="text-xs leading-relaxed whitespace-pre-wrap">
                              {expandedChunk === idx ? chunk.text : chunk.text.slice(0, 120) + (chunk.text.length > 120 ? '...' : '')}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
