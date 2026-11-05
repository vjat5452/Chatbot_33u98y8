import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { TrendingUp, TrendingDown } from 'lucide-react'

export default function StatCard({ title, value, icon, trend }) {
  const hasTrend = trend !== null && trend !== undefined && trend !== 0
  const isPositive = trend > 0

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && (
          <div className="text-muted-foreground">
            {icon}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {hasTrend ? (
          <p className={`text-xs flex items-center gap-1 mt-1 ${isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
            {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {isPositive ? '+' : ''}{trend}% from last period
          </p>
        ) : (
          <p className="text-xs text-muted-foreground mt-1">No change from last period</p>
        )}
      </CardContent>
    </Card>
  )
}
