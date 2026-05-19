"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Search, X, Loader2, ChevronRight } from "lucide-react"

/* ── Types ──────────────────────────────────────── */

interface MatchingItem {
  subject: string
  body: string
  child_name: string | null
  tags: string[]
  due_date: string | null
}

interface SearchResult {
  id: number
  digest_date: string | null
  created_at: string
  matched_in: string[]
  excerpt: string
  matching_item_count: number
  matching_items: MatchingItem[]
}

interface SearchResponse {
  ok: boolean
  query: string
  total: number
  results: SearchResult[]
}

/* ── Helpers ────────────────────────────────────── */

function highlight(text: string, query: string): string {
  if (!query || !text) return text
  return text // We'll handle highlighting via CSS pseudo-element approach in JSX
}

function HighlightedText({ text, query }: { text: string; query: string }) {
  if (!query || !text) return <span>{text}</span>
  const lower = text.toLowerCase()
  const lowerQuery = query.toLowerCase()
  const idx = lower.indexOf(lowerQuery)
  if (idx === -1) return <span>{text}</span>
  return (
    <span>
      {text.slice(0, idx)}
      <mark className="bg-yellow-200 dark:bg-yellow-800/60 text-foreground rounded-sm px-0.5">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </span>
  )
}

function friendlyDate(dateStr: string | null) {
  if (!dateStr) return ""
  try {
    const d = new Date(dateStr + "T00:00:00")
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
  } catch {
    return dateStr
  }
}

/* ── Component ──────────────────────────────────── */

export function DigestSearch() {
  const [query, setQuery] = useState("")
  const [childFilter, setChildFilter] = useState("")
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const doSearch = useCallback(async (q: string, child: string) => {
    if (!q.trim()) {
      setResults(null)
      setShowResults(false)
      return
    }
    setLoading(true)
    try {
      const params = new URLSearchParams({ q: q.trim(), limit: "10" })
      if (child.trim()) params.set("child_name", child.trim())
      const res = await fetch(`/api/search/digests?${params.toString()}`)
      if (!res.ok) return
      const data: SearchResponse = await res.json()
      if (data.ok) {
        setResults(data.results)
        setTotal(data.total)
        setShowResults(true)
      }
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query.trim()) {
      setResults(null)
      setShowResults(false)
      return
    }
    debounceRef.current = setTimeout(() => {
      doSearch(query, childFilter)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, childFilter, doSearch])

  const clearSearch = () => {
    setQuery("")
    setChildFilter("")
    setResults(null)
    setShowResults(false)
    inputRef.current?.focus()
  }

  return (
    <div className="space-y-3">
      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            ref={inputRef}
            placeholder="Search your digest history..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9 pr-9"
          />
          {(query || loading) && (
            <button
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              onClick={clearSearch}
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <X className="h-4 w-4" />
              )}
            </button>
          )}
        </div>
        <Input
          placeholder="Filter by child..."
          value={childFilter}
          onChange={(e) => setChildFilter(e.target.value)}
          className="w-40 shrink-0 hidden sm:block"
        />
      </div>

      {/* Results */}
      {showResults && results !== null && (
        <Card className="border-border/50">
          <CardContent className="p-0">
            {results.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-sm text-muted-foreground">
                  No digests found for &ldquo;{query}&rdquo;
                  {childFilter && ` for child "${childFilter}"`}.
                </p>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/40">
                  <p className="text-xs text-muted-foreground">
                    {total} result{total !== 1 ? "s" : ""} for &ldquo;<strong>{query}</strong>&rdquo;
                    {childFilter && ` · child: "${childFilter}"`}
                  </p>
                  <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={clearSearch}>
                    Clear
                  </Button>
                </div>
                <div className="divide-y divide-border/40">
                  {results.map((result) => (
                    <div key={result.id} className="px-4 py-3 hover:bg-muted/30 transition-colors">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="text-sm font-medium">{friendlyDate(result.digest_date)}</p>
                            {result.matched_in.map((m) => (
                              <Badge key={m} variant="outline" className="text-[10px] h-4 px-1.5">
                                {m}
                              </Badge>
                            ))}
                            {result.matching_item_count > 0 && (
                              <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                                {result.matching_item_count} match{result.matching_item_count !== 1 ? "es" : ""}
                              </Badge>
                            )}
                          </div>
                          {result.excerpt && (
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              <HighlightedText text={result.excerpt} query={query} />
                            </p>
                          )}
                          {result.matching_items.length > 0 && (
                            <div className="mt-1.5 space-y-1">
                              {result.matching_items.slice(0, 2).map((item, idx) => (
                                <div key={idx} className="flex items-start gap-2 text-xs rounded bg-muted/40 px-2 py-1.5">
                                  <span className="shrink-0">
                                    {item.tags.includes("event") ? "📅" : item.tags.includes("action") ? "🔴" : "💬"}
                                  </span>
                                  <div className="min-w-0">
                                    <HighlightedText text={item.subject} query={query} />
                                    {item.child_name && (
                                      <span className="ml-1.5 text-muted-foreground">· {item.child_name}</span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <Link
                          href={`/digest`}
                          className="shrink-0 flex items-center gap-1 text-xs text-primary hover:underline"
                        >
                          View <ChevronRight className="h-3 w-3" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
                {total > 10 && (
                  <div className="px-4 py-2.5 border-t border-border/40 text-center">
                    <p className="text-xs text-muted-foreground">
                      Showing 10 of {total} results. Refine your search to narrow down.
                    </p>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
