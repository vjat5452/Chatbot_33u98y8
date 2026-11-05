import { useState, useEffect, useCallback, useRef } from 'react'
import { getLeads, getExportUrl } from '../api'
import LeadTable from '../components/LeadTable'
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Download, Search, Loader2, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

export default function Leads() {
  const [data, setData] = useState({ total: 0, leads: [] })
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    status: '',
    search: '',
    min_score: '',
    max_score: '',
    sort: 'created_at',
    order: 'desc',
    limit: 10,
    offset: 0,
  })

  // Debounced search
  const [searchInput, setSearchInput] = useState('')
  const searchTimer = useRef(null)

  function handleSearchChange(value) {
    setSearchInput(value)
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => {
      setFilters(f => ({ ...f, search: value, offset: 0 }))
    }, 300)
  }

  const fetchLeads = useCallback(() => {
    setLoading(true)
    getLeads(filters)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters])

  useEffect(() => { fetchLeads() }, [fetchLeads])

  function handleSort(field) {
    setFilters(f => ({
      ...f,
      sort: field,
      order: f.sort === field && f.order === 'desc' ? 'asc' : 'desc',
      offset: 0,
    }))
  }

  function handleFilter(key, value) {
    setFilters(f => ({ ...f, [key]: value, offset: 0 }))
  }

  const totalPages = Math.ceil(data.total / filters.limit) || 1
  const currentPage = Math.floor(filters.offset / filters.limit) + 1

  function goToPage(page) {
    const p = Math.max(1, Math.min(page, totalPages))
    setFilters(f => ({ ...f, offset: (p - 1) * f.limit }))
  }

  // Generate visible page numbers (show at most 5 around current)
  function getPageNumbers() {
    const pages = []
    let start = Math.max(1, currentPage - 2)
    let end = Math.min(totalPages, currentPage + 2)
    if (end - start < 4) {
      if (start === 1) end = Math.min(totalPages, start + 4)
      else start = Math.max(1, end - 4)
    }
    for (let i = start; i <= end; i++) pages.push(i)
    return pages
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Leads</h1>
          <p className="text-sm text-muted-foreground mt-1">{data.total} total leads</p>
        </div>
        <Button asChild variant="default" size="sm">
          <a href={getExportUrl()}>
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </a>
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-4 mb-5">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Search</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Name, email, phone..."
                value={searchInput}
                onChange={e => handleSearchChange(e.target.value)}
                className="pl-9 w-56"
              />
            </div>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Status</Label>
            <Select value={filters.status || "all"} onValueChange={v => handleFilter('status', v === 'all' ? '' : v)}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="engaged">Engaged</SelectItem>
                <SelectItem value="qualified">Qualified</SelectItem>
                <SelectItem value="hot">Hot</SelectItem>
                <SelectItem value="converted">Converted</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Min Score</Label>
            <Input
              type="number"
              min="0"
              max="100"
              placeholder="0"
              value={filters.min_score}
              onChange={e => handleFilter('min_score', e.target.value)}
              className="w-20"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground uppercase tracking-wider mb-1.5 block">Max Score</Label>
            <Input
              type="number"
              min="0"
              max="100"
              placeholder="100"
              value={filters.max_score}
              onChange={e => handleFilter('max_score', e.target.value)}
              className="w-20"
            />
          </div>
        </div>
      </Card>

      {/* Table */}
      {loading ? (
        <div className="text-center text-muted-foreground py-16">
          <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" />
          Loading leads...
        </div>
      ) : (
        <LeadTable
          leads={data.leads}
          onSort={handleSort}
          sortField={filters.sort}
          sortOrder={filters.order}
        />
      )}

      {/* Pagination bar */}
      <div className="flex items-center justify-between mt-4">
        {/* Rows per page */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Rows per page</span>
          <Select value={String(filters.limit)} onValueChange={v => setFilters(f => ({ ...f, limit: Number(v), offset: 0 }))}>
            <SelectTrigger className="w-[70px] h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="20">20</SelectItem>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-sm text-muted-foreground ml-2">
            {data.total > 0
              ? `${filters.offset + 1}-${Math.min(filters.offset + filters.limit, data.total)} of ${data.total}`
              : '0 results'
            }
          </span>
        </div>

        {/* Page navigation */}
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={currentPage <= 1}
            onClick={() => goToPage(1)}
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={currentPage <= 1}
            onClick={() => goToPage(currentPage - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          {getPageNumbers().map(page => (
            <Button
              key={page}
              variant={page === currentPage ? 'default' : 'outline'}
              size="icon"
              className="h-8 w-8 text-sm"
              onClick={() => goToPage(page)}
            >
              {page}
            </Button>
          ))}

          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={currentPage >= totalPages}
            onClick={() => goToPage(currentPage + 1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            disabled={currentPage >= totalPages}
            onClick={() => goToPage(totalPages)}
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
