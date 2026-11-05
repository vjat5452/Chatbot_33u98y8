import { useNavigate } from 'react-router-dom'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Users } from "lucide-react"

const statusDotConfig = {
  new:       { color: 'bg-blue-500',    label: 'New' },
  engaged:   { color: 'bg-yellow-500',  label: 'Engaged' },
  qualified: { color: 'bg-emerald-500', label: 'Qualified' },
  hot:       { color: 'bg-red-500',     label: 'Hot' },
  converted: { color: 'bg-emerald-500', label: 'Converted' },
}

function StatusIndicator({ status }) {
  const config = statusDotConfig[status] || { color: 'bg-muted-foreground', label: status }
  return (
    <div className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full ${config.color}`} />
      <span className="capitalize">{config.label}</span>
    </div>
  )
}

function ScoreBadge({ score }) {
  let cls = 'text-muted-foreground bg-muted'
  if (score >= 60) cls = 'text-orange-700 bg-orange-50 font-bold'
  else if (score >= 40) cls = 'text-yellow-700 bg-yellow-50 font-semibold'
  else if (score > 20) cls = 'text-blue-700 bg-blue-50'
  return <span className={`inline-flex items-center justify-center w-10 h-6 rounded-md text-xs ${cls}`}>{score}</span>
}

export default function LeadTable({ leads, onSort, sortField, sortOrder }) {
  const navigate = useNavigate()

  const headers = [
    { key: 'name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'phone', label: 'Phone' },
    { key: 'lead_score', label: 'Score' },
    { key: 'status', label: 'Status' },
    { key: 'source_page', label: 'Page' },
    { key: 'created_at', label: 'Created' },
  ]

  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {headers.map(h => (
              <TableHead
                key={h.key}
                onClick={() => onSort?.(h.key)}
                className="cursor-pointer select-none text-xs hover:text-foreground"
              >
                <span className="inline-flex items-center gap-1">
                  {h.label}
                  {sortField === h.key && (
                    <span className="text-primary">{sortOrder === 'asc' ? '\u2191' : '\u2193'}</span>
                  )}
                </span>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {leads.length === 0 ? (
            <TableRow>
              <TableCell colSpan={headers.length} className="h-32 text-center text-muted-foreground">
                <Users className="w-8 h-8 mx-auto mb-2 opacity-40" />
                No leads found
              </TableCell>
            </TableRow>
          ) : (
            leads.map(lead => (
              <TableRow
                key={lead.id}
                onClick={() => navigate(`/leads/${lead.id}`)}
                className="cursor-pointer"
              >
                <TableCell className="font-medium">
                  {lead.name || <span className="text-muted-foreground italic">Unknown</span>}
                </TableCell>
                <TableCell className="text-muted-foreground">{lead.email || <span className="opacity-40">-</span>}</TableCell>
                <TableCell className="text-muted-foreground">{lead.phone || <span className="opacity-40">-</span>}</TableCell>
                <TableCell>
                  <ScoreBadge score={lead.lead_score} />
                </TableCell>
                <TableCell>
                  <StatusIndicator status={lead.status} />
                </TableCell>
                <TableCell className="text-muted-foreground max-w-[150px] truncate">
                  {lead.source_page || <span className="opacity-40">-</span>}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '-'}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
