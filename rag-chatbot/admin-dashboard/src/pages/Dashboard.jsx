import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid } from 'recharts'
import { getDashboard, getAnalytics, getRecentLeads, getHotLeads } from '../api'
import StatCard from '../components/StatCard'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent } from "@/components/ui/chart"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Users, Flame, MessageSquare, ThumbsUp, Activity, Loader2 } from 'lucide-react'

const messagesChartConfig = {
  count: {
    label: "Messages",
    color: "hsl(var(--chart-1))",
  },
}

const funnelChartConfig = {
  new:       { label: "New",       color: "hsl(210 100% 80%)" },  // light sky blue
  engaged:   { label: "Engaged",   color: "hsl(215 90% 65%)" },   // medium blue
  qualified: { label: "Qualified", color: "hsl(220 85% 50%)" },   // strong blue
  hot:       { label: "Hot",       color: "hsl(225 80% 38%)" },   // dark blue
  converted: { label: "Converted", color: "hsl(230 75% 25%)" },   // navy
}

// Status dot colors matching the shadcn template pattern
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
      <span className="text-sm capitalize">{config.label}</span>
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

function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function LeadsTable({ leads, navigate }) {
  if (leads.length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-8">
        <Users className="w-8 h-8 mx-auto mb-2 opacity-40" />
        No leads found
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Name</TableHead>
          <TableHead>Score</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Source</TableHead>
          <TableHead>Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {leads.map(lead => (
          <TableRow
            key={lead.id}
            className="cursor-pointer"
            onClick={() => navigate(`/leads/${lead.id}`)}
          >
            <TableCell>
              <div className="flex items-center gap-3">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="text-xs">{getInitials(lead.name)}</AvatarFallback>
                </Avatar>
                <div>
                  <div className="font-medium">{lead.name || 'Anonymous'}</div>
                  {lead.email && <div className="text-xs text-muted-foreground">{lead.email}</div>}
                </div>
              </div>
            </TableCell>
            <TableCell>
              <ScoreBadge score={lead.lead_score} />
            </TableCell>
            <TableCell>
              <StatusIndicator status={lead.status} />
            </TableCell>
            <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
              {lead.source_page || '—'}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {formatDate(lead.created_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [recentLeads, setRecentLeads] = useState(null)
  const [hotLeads, setHotLeads] = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState('30')

  // Initial load
  useEffect(() => {
    Promise.all([getDashboard(), getAnalytics(30), getRecentLeads(5), getHotLeads(5)])
      .then(([s, a, rl, hl]) => { setStats(s); setAnalytics(a); setRecentLeads(rl); setHotLeads(hl) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // Refresh chart when date range changes
  const handleDaysChange = useCallback((value) => {
    setDays(value)
    getAnalytics(Number(value)).then(setAnalytics).catch(console.error)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" />
          Loading dashboard...
        </div>
      </div>
    )
  }

  const funnelData = analytics?.lead_funnel
    ? Object.entries(analytics.lead_funnel).map(([name, value]) => ({
        name,
        value,
        fill: funnelChartConfig[name]?.color || 'hsl(220 85% 50%)',
      }))
    : []

  const recent = recentLeads?.leads || []
  const hot = hotLeads?.leads || []

  return (
    <div>
      {/* Header with date range tabs */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Overview of your chatbot performance and leads</p>
        </div>
        <Tabs value={days} onValueChange={handleDaysChange}>
          <TabsList>
            <TabsTrigger value="7">7d</TabsTrigger>
            <TabsTrigger value="14">14d</TabsTrigger>
            <TabsTrigger value="30">30d</TabsTrigger>
            <TabsTrigger value="90">90d</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Stat cards — 5 across */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
        <StatCard
          title="Total Leads"
          value={stats?.total_leads ?? 0}
          icon={<Users className="h-4 w-4" />}
          trend={stats?.total_leads_trend}
        />
        <StatCard
          title="Hot Leads"
          value={stats?.hot_leads ?? 0}
          icon={<Flame className="h-4 w-4" />}
          trend={stats?.hot_leads_trend}
        />
        <StatCard
          title="Messages Today"
          value={stats?.messages_today ?? 0}
          icon={<MessageSquare className="h-4 w-4" />}
          trend={stats?.messages_today_trend}
        />
        <StatCard
          title="Satisfaction"
          value={`${stats?.satisfaction_rate ?? 0}%`}
          icon={<ThumbsUp className="h-4 w-4" />}
          trend={stats?.satisfaction_rate_trend}
        />
        <StatCard
          title="Active Sessions"
          value={stats?.active_sessions_today ?? 0}
          icon={<Activity className="h-4 w-4" />}
          trend={stats?.active_sessions_today_trend}
        />
      </div>

      {/* Charts row — area chart (2/3) + funnel donut (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Messages Area Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Messages Over Time</CardTitle>
            <CardDescription>User messages in the last {days} days</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={messagesChartConfig} className="h-[300px] w-full">
              <AreaChart data={analytics?.messages_per_day || []} accessibilityLayer>
                <defs>
                  <linearGradient id="fillMessages" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-count)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--color-count)" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  tickFormatter={d => d?.slice(5)}
                />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="var(--color-count)"
                  strokeWidth={2}
                  fill="url(#fillMessages)"
                />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Lead Funnel Donut */}
        <Card>
          <CardHeader>
            <CardTitle>Lead Funnel</CardTitle>
            <CardDescription>Distribution by status</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={funnelChartConfig} className="mx-auto aspect-square h-[250px]">
              <PieChart accessibilityLayer>
                <ChartTooltip content={<ChartTooltipContent nameKey="name" hideLabel />} />
                <Pie
                  data={funnelData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                  nameKey="name"
                >
                  {funnelData.map(entry => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Pie>
                <ChartLegend content={<ChartLegendContent nameKey="name" />} />
              </PieChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>

      {/* Single card with tabs: Recent Leads / Hot Leads */}
      <Card>
        <Tabs defaultValue="recent">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle>Leads</CardTitle>
              <CardDescription>Browse recent and top-performing leads</CardDescription>
            </div>
            <TabsList>
              <TabsTrigger value="recent">
                Recent Leads
                {recent.length > 0 && (
                  <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-[10px]">{recent.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="hot">
                Hot Leads
                {hot.length > 0 && (
                  <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-[10px]">{hot.length}</Badge>
                )}
              </TabsTrigger>
            </TabsList>
          </CardHeader>
          <CardContent>
            <TabsContent value="recent" className="mt-0">
              <LeadsTable leads={recent} navigate={navigate} />
            </TabsContent>
            <TabsContent value="hot" className="mt-0">
              <LeadsTable leads={hot} navigate={navigate} />
            </TabsContent>
          </CardContent>
        </Tabs>
      </Card>
    </div>
  )
}
