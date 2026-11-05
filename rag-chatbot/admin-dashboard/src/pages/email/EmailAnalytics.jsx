import { useState, useEffect, useCallback } from 'react'
import { AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid } from 'recharts'
import { getEmailAnalyticsOverview, getEmailWarmVsCold, getEmailVolume, getEmailDomainHealth, getEmailRankings, getEmailSendTimes } from '../../api'
import StatCard from '../../components/StatCard'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Table, TableHeader, TableBody, TableHead, TableRow, TableCell } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Send, Eye, MousePointerClick, AlertTriangle, Loader2 } from 'lucide-react'

const volumeChartConfig = {
  sent: { label: 'Sent', color: 'hsl(220 85% 50%)' },
  opened: { label: 'Opened', color: 'hsl(150 60% 45%)' },
  clicked: { label: 'Clicked', color: 'hsl(280 60% 50%)' },
}

const comparisonConfig = {
  warm: { label: 'Warm', color: 'hsl(25 90% 55%)' },
  cold: { label: 'Cold', color: 'hsl(200 80% 50%)' },
}

const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function HeatmapCell({ value, max }) {
  const intensity = max > 0 ? value / max : 0
  const bg = `rgba(37, 99, 235, ${Math.max(intensity, 0.05)})`
  return (
    <div
      className="w-6 h-6 rounded-sm text-[8px] flex items-center justify-center"
      style={{ backgroundColor: bg, color: intensity > 0.5 ? '#fff' : '#6b7280' }}
      title={`${value} opens`}
    >
      {value > 0 ? value : ''}
    </div>
  )
}

export default function EmailAnalytics() {
  const [overview, setOverview] = useState(null)
  const [warmCold, setWarmCold] = useState(null)
  const [volume, setVolume] = useState(null)
  const [domains, setDomains] = useState(null)
  const [rankings, setRankings] = useState(null)
  const [heatmap, setHeatmap] = useState(null)
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState('30')
  const [tab, setTab] = useState('overview')

  const loadData = useCallback(async (d) => {
    try {
      const [o, wc, v, dom, r, h] = await Promise.all([
        getEmailAnalyticsOverview(Number(d)),
        getEmailWarmVsCold(Number(d)),
        getEmailVolume(Number(d)),
        getEmailDomainHealth(Number(d)),
        getEmailRankings(Number(d)),
        getEmailSendTimes(90),
      ])
      setOverview(o)
      setWarmCold(wc)
      setVolume(v)
      setDomains(dom)
      setRankings(r)
      setHeatmap(h)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadData(period) }, [loadData, period])

  function handlePeriodChange(value) {
    setPeriod(value)
    setLoading(true)
  }

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>

  // Build heatmap grid
  const heatmapGrid = Array.from({ length: 7 }, () => Array(24).fill(0))
  let heatmapMax = 1
  if (heatmap) {
    for (const h of heatmap) {
      heatmapGrid[h.day][h.hour] = h.opens
      if (h.opens > heatmapMax) heatmapMax = h.opens
    }
  }

  // Warm vs cold comparison chart data
  const comparisonData = warmCold ? [
    { metric: 'Open Rate', warm: warmCold.warm?.open_rate || 0, cold: warmCold.cold?.open_rate || 0 },
    { metric: 'Click Rate', warm: warmCold.warm?.click_rate || 0, cold: warmCold.cold?.click_rate || 0 },
    { metric: 'Bounce Rate', warm: warmCold.warm?.bounce_rate || 0, cold: warmCold.cold?.bounce_rate || 0 },
  ] : []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Email Analytics</h1>
          <p className="text-sm text-muted-foreground">Performance metrics across all campaigns</p>
        </div>
        <Tabs value={period} onValueChange={handlePeriodChange}>
          <TabsList>
            <TabsTrigger value="7">7d</TabsTrigger>
            <TabsTrigger value="14">14d</TabsTrigger>
            <TabsTrigger value="30">30d</TabsTrigger>
            <TabsTrigger value="90">90d</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Sent" value={overview?.total_sent ?? 0} icon={<Send className="h-4 w-4" />} />
        <StatCard title="Avg Open Rate" value={`${overview?.avg_open_rate ?? 0}%`} icon={<Eye className="h-4 w-4" />} />
        <StatCard title="Avg Click Rate" value={`${overview?.avg_click_rate ?? 0}%`} icon={<MousePointerClick className="h-4 w-4" />} />
        <StatCard title="Bounce Rate" value={`${overview?.avg_bounce_rate ?? 0}%`} icon={<AlertTriangle className="h-4 w-4" />} />
      </div>

      <Tabs value={tab} onValueChange={setTab} className="mb-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="comparison">Warm vs Cold</TabsTrigger>
          <TabsTrigger value="heatmap">Send Times</TabsTrigger>
          <TabsTrigger value="domains">Domain Health</TabsTrigger>
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview" className="mt-4 space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Send volume */}
            <Card>
              <CardHeader>
                <CardTitle>Send Volume</CardTitle>
                <CardDescription>Emails sent per day</CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={volumeChartConfig} className="h-[300px] w-full">
                  <AreaChart data={volume || []}>
                    <defs>
                      <linearGradient id="fillSent" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--color-sent)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--color-sent)" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="date" tickLine={false} axisLine={false} tickFormatter={d => d?.slice(5)} />
                    <YAxis tickLine={false} axisLine={false} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Area type="monotone" dataKey="sent" stroke="var(--color-sent)" fill="url(#fillSent)" strokeWidth={2} />
                    <Area type="monotone" dataKey="opened" stroke="var(--color-opened)" fill="none" strokeWidth={2} strokeDasharray="4 4" />
                  </AreaChart>
                </ChartContainer>
              </CardContent>
            </Card>

            {/* Campaign rankings */}
            <Card>
              <CardHeader>
                <CardTitle>Top Campaigns</CardTitle>
                <CardDescription>Ranked by open rate</CardDescription>
              </CardHeader>
              <CardContent>
                {rankings && rankings.length > 0 ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Campaign</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Opens</TableHead>
                        <TableHead>Clicks</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {rankings.map(r => (
                        <TableRow key={r.id}>
                          <TableCell className="font-medium text-sm">{r.name}</TableCell>
                          <TableCell><Badge variant={r.campaign_type === 'warm' ? 'default' : 'secondary'} className="text-[10px]">{r.campaign_type}</Badge></TableCell>
                          <TableCell className="text-sm text-emerald-600 font-medium">{r.open_rate}%</TableCell>
                          <TableCell className="text-sm text-blue-600 font-medium">{r.click_rate}%</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <div className="py-8 text-center text-muted-foreground text-sm">No campaign data yet</div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Warm vs Cold */}
        <TabsContent value="comparison" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Warm vs Cold Comparison</CardTitle>
              <CardDescription>Side-by-side campaign type performance</CardDescription>
            </CardHeader>
            <CardContent>
              {comparisonData.length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <ChartContainer config={comparisonConfig} className="h-[300px] w-full">
                    <BarChart data={comparisonData}>
                      <CartesianGrid vertical={false} />
                      <XAxis dataKey="metric" tickLine={false} axisLine={false} />
                      <YAxis tickLine={false} axisLine={false} unit="%" />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Bar dataKey="warm" fill="var(--color-warm)" radius={4} />
                      <Bar dataKey="cold" fill="var(--color-cold)" radius={4} />
                    </BarChart>
                  </ChartContainer>
                  <div className="space-y-4">
                    {['warm', 'cold'].map(type => (
                      <Card key={type}>
                        <CardContent className="p-4">
                          <h4 className="font-semibold text-sm capitalize mb-2">{type} Campaigns</h4>
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div><div className="text-lg font-bold">{warmCold?.[type]?.total_sent || 0}</div><div className="text-[10px] text-muted-foreground">Sent</div></div>
                            <div><div className="text-lg font-bold text-emerald-600">{warmCold?.[type]?.open_rate || 0}%</div><div className="text-[10px] text-muted-foreground">Open Rate</div></div>
                            <div><div className="text-lg font-bold text-blue-600">{warmCold?.[type]?.click_rate || 0}%</div><div className="text-[10px] text-muted-foreground">Click Rate</div></div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center text-muted-foreground text-sm">No comparison data yet</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Heatmap */}
        <TabsContent value="heatmap" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Send-Time Heatmap</CardTitle>
              <CardDescription>Email opens by day and hour (last 90 days)</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <div className="inline-flex flex-col gap-1">
                  {/* Hour labels */}
                  <div className="flex gap-1 ml-12">
                    {Array.from({ length: 24 }, (_, h) => (
                      <div key={h} className="w-6 text-center text-[8px] text-muted-foreground">{h}</div>
                    ))}
                  </div>
                  {/* Grid */}
                  {heatmapGrid.map((row, dayIdx) => (
                    <div key={dayIdx} className="flex items-center gap-1">
                      <span className="w-10 text-xs text-muted-foreground text-right">{days[dayIdx]}</span>
                      <div className="flex gap-1">
                        {row.map((val, hourIdx) => (
                          <HeatmapCell key={hourIdx} value={val} max={heatmapMax} />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Domain Health */}
        <TabsContent value="domains" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Domain Health</CardTitle>
              <CardDescription>Bounce and open rates by recipient domain</CardDescription>
            </CardHeader>
            <CardContent>
              {domains && domains.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Domain</TableHead>
                      <TableHead>Total</TableHead>
                      <TableHead>Open Rate</TableHead>
                      <TableHead>Bounce Rate</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {domains.map(d => (
                      <TableRow key={d.domain}>
                        <TableCell className="font-medium text-sm">{d.domain}</TableCell>
                        <TableCell className="text-sm">{d.total}</TableCell>
                        <TableCell className="text-sm text-emerald-600">{d.open_rate}%</TableCell>
                        <TableCell className={`text-sm ${d.bounce_rate > 5 ? 'text-red-600 font-medium' : ''}`}>{d.bounce_rate}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="py-8 text-center text-muted-foreground text-sm">No domain data yet</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
