import { useState, useEffect, useCallback } from 'react'
import { getConversations, getConversation } from '../api'
import ChatViewer from '../components/ChatViewer'
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MessageSquare, Loader2, RefreshCw } from 'lucide-react'

export default function Conversations() {
  const [data, setData] = useState({ total: 0, conversations: [] })
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingChat, setLoadingChat] = useState(false)
  const [offset, setOffset] = useState(0)
  const limit = 30

  const fetchConversations = useCallback((showLoader = true) => {
    if (showLoader) setLoading(true)
    getConversations({ limit, offset })
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [offset])

  // Initial fetch + auto-refresh every 15 seconds
  useEffect(() => {
    fetchConversations(true)
    const interval = setInterval(() => fetchConversations(false), 15000)
    return () => clearInterval(interval)
  }, [fetchConversations])

  async function selectConversation(sessionId) {
    setSelected(sessionId)
    setLoadingChat(true)
    try {
      const result = await getConversation(sessionId)
      setMessages(result.messages)
    } catch (e) {
      console.error(e)
      setMessages([])
    } finally {
      setLoadingChat(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Conversations</h1>
          <p className="text-sm text-muted-foreground mt-1">{data.total} total conversations</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchConversations(true)} disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Conversation list */}
        <div className="lg:col-span-1">
          <Card className="overflow-hidden">
            <div className="px-4 py-3 border-b">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{data.total} conversations</p>
            </div>
            <ScrollArea className="h-[600px]">
              {loading ? (
                <div className="px-4 py-12 text-center text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                  Loading...
                </div>
              ) : data.conversations.length === 0 ? (
                <div className="px-4 py-12 text-center text-muted-foreground">No conversations yet</div>
              ) : (
                data.conversations.map(conv => (
                  <button
                    key={conv.session_id}
                    onClick={() => selectConversation(conv.session_id)}
                    className={`w-full text-left px-4 py-3.5 border-b border-border/50 hover:bg-muted/50 transition-colors ${
                      selected === conv.session_id ? 'bg-muted border-l-2 border-l-primary' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium truncate max-w-[180px]">
                        {conv.lead?.name || conv.session_id.slice(0, 12)}
                      </span>
                      <Badge variant="secondary" className="text-[11px]">
                        {conv.message_count} msgs
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">{conv.preview}</p>
                    <p className="text-[11px] text-muted-foreground/50 mt-1">
                      {conv.last_message_at ? new Date(conv.last_message_at).toLocaleString() : ''}
                    </p>
                    {conv.lead && (
                      <div className="flex items-center gap-2 mt-1.5">
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                          {conv.lead.status}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">Score: {conv.lead.lead_score}</span>
                      </div>
                    )}
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

        {/* Chat viewer */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="border-b">
              <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                {selected ? `Session: ${selected}` : 'Select a conversation'}
              </CardTitle>
            </CardHeader>
            {!selected ? (
              <div className="py-20 text-center text-muted-foreground">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
                Click a conversation on the left to view messages
              </div>
            ) : loadingChat ? (
              <div className="py-20 text-center text-muted-foreground">
                <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" />
                Loading messages...
              </div>
            ) : (
              <ChatViewer messages={messages} />
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
