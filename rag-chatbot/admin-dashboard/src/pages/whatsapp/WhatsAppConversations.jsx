import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getWhatsAppStatus, getWhatsAppConversations } from '../../api'
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table"
import { MessageCircle, Loader2, Search, RefreshCw } from 'lucide-react'

export default function WhatsAppConversations() {
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [data, setData] = useState({ total: 0, conversations: [] })
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const limit = 20

  const fetchData = useCallback(async (showLoader = true) => {
    if (showLoader) setLoading(true)
    try {
      const [s, c] = await Promise.all([
        getWhatsAppStatus().catch(() => null),
        getWhatsAppConversations(page, search)
      ])
      setStatus(s)
      setData(c)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    fetchData(true)
    const interval = setInterval(() => fetchData(false), 15000)
    return () => clearInterval(interval)
  }, [fetchData])

  function handleSearch(e) {
    e.preventDefault()
    setPage(1)
    fetchData(true)
  }

  const totalPages = Math.ceil(data.total / limit)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">WhatsApp Conversations</h1>
          {status && (
            <Badge variant={status.connected ? 'default' : 'destructive'} className="gap-1.5">
              <span className={`w-2 h-2 rounded-full ${status.connected ? 'bg-green-400' : 'bg-red-400'}`} />
              {status.connected ? `Connected (${status.phone_number})` : 'Disconnected'}
            </Badge>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchData(true)}>
          <RefreshCw className="w-4 h-4 mr-1" /> Refresh
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Conversations ({data.total})</CardTitle>
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search phone..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="pl-8 pr-3 py-2 text-sm border rounded-md bg-background w-48"
                />
              </div>
            </form>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : data.conversations.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <MessageCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-lg font-medium mb-1">No conversations yet</p>
              <p className="text-sm">Start the WhatsApp bridge and send a message to get started.</p>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Phone Number</TableHead>
                    <TableHead>Last Message</TableHead>
                    <TableHead className="text-center">Messages</TableHead>
                    <TableHead>Last Active</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.conversations.map(c => (
                    <TableRow
                      key={c.session_id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => navigate(`/whatsapp/${c.session_id}`)}
                    >
                      <TableCell className="font-medium">+{c.phone}</TableCell>
                      <TableCell className="max-w-xs truncate text-muted-foreground">{c.last_message}</TableCell>
                      <TableCell className="text-center">
                        <Badge variant="secondary">{c.message_count}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(c.last_active).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                      Previous
                    </Button>
                    <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
