import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getWhatsAppChat } from '../../api'
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Loader2, MessageCircle } from 'lucide-react'

export default function WhatsAppChat() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const [phone, setPhone] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    getWhatsAppChat(sessionId)
      .then(data => {
        setMessages(data.messages || [])
        setPhone(data.phone || sessionId.replace('wa_', ''))
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [sessionId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Button variant="outline" size="sm" onClick={() => navigate('/whatsapp')}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">+{phone}</h1>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <MessageCircle className="w-4 h-4" />
            Chat History ({messages.length} messages)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : messages.length === 0 ? (
            <p className="text-center py-12 text-muted-foreground">No messages found.</p>
          ) : (
            <div ref={scrollRef} className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-md'
                        : 'bg-muted text-foreground rounded-bl-md'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <p className={`text-[10px] mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-muted-foreground'}`}>
                      {new Date(msg.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
