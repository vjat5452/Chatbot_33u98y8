import { useState, useEffect } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { getAnalytics } from '../api'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2 } from 'lucide-react'

const messagesChartConfig = {
  count: { label: "Messages", color: "hsl(var(--chart-1))" },
}

const peakHoursChartConfig = {
  count: { label: "Messages", color: "hsl(var(--chart-3))" },
}

const topicsChartConfig = {
  count: { label: "Mentions", color: "hsl(var(--chart-4))" },
}

const satisfactionChartConfig = {
  rate: { label: "Satisfaction", color: "hsl(var(--chart-2))" },
}

const pagesChartConfig = {
  count: { label: "Visits", color: "hsl(var(--chart-5))" },
}

export default function Analytics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState('30')

  useEffect(() => {
    setLoading(true)
    getAnalytics(Number(days))
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days])

  if (loading) {
    return (
      <div className="text-center text-muted-foreground py-16">
        <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" />
        Loading analytics...
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">Chatbot performance insights</p>
        </div>
        <Tabs value={days} onValueChange={setDays}>
          <TabsList>
            <TabsTrigger value="7">7d</TabsTrigger>
            <TabsTrigger value="14">14d</TabsTrigger>
            <TabsTrigger value="30">30d</TabsTrigger>
            <TabsTrigger value="90">90d</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Messages Over Time - Line Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Messages Over Time</CardTitle>
            <CardDescription>Daily message volume</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={messagesChartConfig} className="!aspect-auto h-[280px] w-full">
              <LineChart data={data?.messages_per_day || []} accessibilityLayer>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} tickFormatter={d => d?.slice(5)} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Line type="natural" dataKey="count" stroke="var(--color-count)" strokeWidth={2} dot={false} />
              </LineChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Peak Hours - Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Peak Hours</CardTitle>
            <CardDescription>Activity by hour of day</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={peakHoursChartConfig} className="!aspect-auto h-[280px] w-full">
              <BarChart data={data?.peak_hours || []} accessibilityLayer>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="hour" tickLine={false} axisLine={false} tickMargin={8} tickFormatter={h => `${h}:00`} />
                <YAxis tickLine={false} axisLine={false} tickMargin={8} />
                <ChartTooltip content={<ChartTooltipContent labelFormatter={h => `${h}:00`} />} />
                <Bar dataKey="count" fill="var(--color-count)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Topic Distribution - Horizontal Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Topic Distribution</CardTitle>
            <CardDescription>Most discussed topics</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={topicsChartConfig} className="!aspect-auto h-[280px] w-full">
              <BarChart data={data?.popular_topics || []} layout="vertical" accessibilityLayer>
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis dataKey="topic" type="category" tickLine={false} axisLine={false} width={100} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--color-count)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Satisfaction Trend - Line Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Satisfaction Trend</CardTitle>
            <CardDescription>User satisfaction over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={satisfactionChartConfig} className="!aspect-auto h-[280px] w-full">
              <LineChart data={data?.satisfaction_trend || []} accessibilityLayer margin={{ top: 20, right: 12, bottom: 5, left: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={8} tickFormatter={d => d?.slice(5)} />
                <YAxis tickLine={false} axisLine={false} tickMargin={4} domain={[0, 100]} tickFormatter={v => `${v}%`} width={45} />
                <ChartTooltip content={<ChartTooltipContent formatter={v => `${v}%`} />} />
                <Line type="natural" dataKey="rate" stroke="var(--color-rate)" strokeWidth={2} dot={false} />
              </LineChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Busiest Pages - Horizontal Bar Chart (full width) */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Busiest Pages</CardTitle>
            <CardDescription>Pages with most chatbot interactions</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={pagesChartConfig} className="!aspect-auto h-[280px] w-full">
              <BarChart data={data?.busiest_pages || []} layout="vertical" accessibilityLayer>
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} tickMargin={8} />
                <YAxis dataKey="page_url" type="category" tickLine={false} axisLine={false} width={200} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--color-count)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
