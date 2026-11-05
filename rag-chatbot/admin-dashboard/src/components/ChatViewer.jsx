import { useRef, useEffect } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { MessageSquare, Zap, User } from "lucide-react"

function renderMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" class="underline">$1</a>')
    .replace(/\n/g, '<br/>')
}

export default function ChatViewer({ messages }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!messages || messages.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-12">
        <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-40" />
        No messages in this conversation
      </div>
    )
  }

  return (
    <ScrollArea className="h-[500px]">
      <div className="space-y-3 p-5 overflow-hidden">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role !== 'user' && (
              <Avatar className="h-7 w-7 mr-2 mt-1 shrink-0">
                <AvatarFallback className="bg-muted text-muted-foreground">
                  <Zap className="h-3.5 w-3.5" />
                </AvatarFallback>
              </Avatar>
            )}
            <div
              className={`max-w-[75%] min-w-0 rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground rounded-br-md'
                  : 'bg-muted text-foreground rounded-bl-md'
              }`}
              style={{ overflowWrap: 'anywhere', wordBreak: 'break-word' }}
            >
              <div
                className="[&_a]:underline [&_a]:text-blue-400"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
              />
              {msg.timestamp && (
                <p className={`text-[10px] mt-1.5 ${msg.role === 'user' ? 'text-primary-foreground/60' : 'text-muted-foreground'}`}>
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </p>
              )}
            </div>
            {msg.role === 'user' && (
              <Avatar className="h-7 w-7 ml-2 mt-1 shrink-0">
                <AvatarFallback className="bg-primary text-primary-foreground">
                  <User className="h-3.5 w-3.5" />
                </AvatarFallback>
              </Avatar>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}
