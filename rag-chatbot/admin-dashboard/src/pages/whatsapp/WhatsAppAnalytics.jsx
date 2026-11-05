import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getWhatsAppAnalytics } from '../../api'
import StatCard from '../../components/StatCard'
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { MessageCircle, Users, MessagesSquare, Clock, Loader2 } from 'lucide-react'

export default function WhatsAppAnalytics() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getWhatsAppAnalytics()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-7 h-7 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!data) return <p className="text-center py-12 text-muted-foreground">Failed to load analytics.</p>

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight mb-6">WhatsApp Analytics</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Conversations" value={data.total_conversations} icon={<Users className="h-4 w-4" />} />
        <StatCard title="Total Messages" value={data.total_messages} icon={<MessagesSquare className="h-4 w-4" />} />
        <StatCard title="Messages Today" value={data.messages_today} icon={<MessageCircle className="h-4 w-4" />} />
        <StatCard title="Avg Response Length" value={`${data.avg_response_length} chars`} icon={<Clock className="h-4 w-4" />} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Conversations</CardTitle>
        </CardHeader>
        <CardContent>
          {data.recent_conversations?.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Phone</TableHead>
                  <TableHead>Last Message</TableHead>
                  <TableHead className="text-center">Messages</TableHead>
                  <TableHead>Last Active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.recent_conversations.map(c => (
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
          ) : (
            <p className="text-center py-8 text-muted-foreground">No conversations yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
