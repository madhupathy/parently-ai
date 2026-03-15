export interface ChildSetupState {
  childId: number
  hasSchoolText: boolean
  hasLinkedSchoolSource: boolean
  hasDiscoveredWebsite: boolean
  hasDiscoveredCalendar: boolean
  hasPendingSchoolSource: boolean
}

export interface SetupStatusModel {
  hasChildren: boolean
  hasSchoolText: boolean
  hasLinkedSchoolSource: boolean
  hasDiscoveredWebsite: boolean
  hasDiscoveredCalendar: boolean
  hasPendingSchoolSource: boolean
  gmailConnected: boolean
  driveConnected: boolean
  digestReady: boolean
  childStates: ChildSetupState[]
}

interface SourceRow {
  status?: string
  homepage_url?: string | null
  calendar_page_url?: string | null
  ics_urls?: string[]
  rss_urls?: string[]
  pdf_urls?: string[]
}

interface ChildRow {
  id: number
  school_name?: string | null
}

function hasCalendarSignal(source: SourceRow) {
  return Boolean(
    source.calendar_page_url ||
      (source.ics_urls && source.ics_urls.length > 0) ||
      (source.rss_urls && source.rss_urls.length > 0) ||
      (source.pdf_urls && source.pdf_urls.length > 0)
  )
}

export async function fetchSetupStatusModel(opts?: {
  grantedScopes?: string
  provider?: string
}): Promise<SetupStatusModel> {
  const [setupRes, childrenRes, integrationsRes] = await Promise.all([
    fetch("/api/setup/status", { cache: "no-store" }).catch(() => null as any),
    fetch("/api/children", { cache: "no-store" }).catch(() => null as any),
    fetch("/api/integrations/status", { cache: "no-store" }).catch(() => null as any),
  ])

  const setupData = setupRes && setupRes.ok ? await setupRes.json() : null
  const childrenData = childrenRes && childrenRes.ok ? await childrenRes.json() : { children: [] }
  const children: ChildRow[] = childrenData?.children || []
  const hasChildren =
    Boolean(setupData?.setup_status?.has_children) || children.length > 0

  const sourcePayloads = await Promise.all(
    children.map((child) =>
      fetch(`/api/sources/${child.id}`, { cache: "no-store" })
        .then((res) => (res.ok ? res.json() : { sources: [] }))
        .catch(() => ({ sources: [] }))
    )
  )

  const childStates: ChildSetupState[] = children.map((child, index) => {
    const sources: SourceRow[] = sourcePayloads[index]?.sources || []
    const linkedSources = sources.filter((s) => s.status === "verified" || s.status === "linked")
    const pendingSources = sources.filter((s) => s.status === "needs_confirmation")
    return {
      childId: child.id,
      hasSchoolText: Boolean((child.school_name || "").trim()),
      hasLinkedSchoolSource: linkedSources.length > 0,
      hasDiscoveredWebsite: sources.some((s) => Boolean(s.homepage_url)),
      hasDiscoveredCalendar: sources.some(hasCalendarSignal),
      hasPendingSchoolSource: pendingSources.length > 0,
    }
  })

  const hasSchoolText = childStates.some((c) => c.hasSchoolText)
  const hasLinkedSchoolSource = childStates.some((c) => c.hasLinkedSchoolSource)
  const hasDiscoveredWebsite = childStates.some((c) => c.hasDiscoveredWebsite)
  const hasDiscoveredCalendar = childStates.some((c) => c.hasDiscoveredCalendar)
  const hasPendingSchoolSource = childStates.some((c) => c.hasPendingSchoolSource)

  const integrationsData =
    integrationsRes && integrationsRes.ok ? await integrationsRes.json() : { integrations: {} }
  const integrations = integrationsData?.integrations || {}
  const scopes = (opts?.grantedScopes || "").toLowerCase()
  const provider = (opts?.provider || "").toLowerCase()

  const gmailByScope =
    provider === "google" && scopes.includes("https://www.googleapis.com/auth/gmail.readonly")
  const driveByScope =
    provider === "google" && scopes.includes("https://www.googleapis.com/auth/drive.readonly")

  const gmailConnected = integrations?.gmail?.status === "connected" || gmailByScope
  const driveConnected = integrations?.gdrive?.status === "connected" || driveByScope

  const digestReady =
    setupData?.setup_status?.digest_ready ??
    (hasChildren && hasLinkedSchoolSource)

  console.debug("[setup-status] dashboard children data", {
    childrenCount: children.length,
    children,
  })
  console.debug("[setup-status] computed setup status", {
    hasChildren,
    hasSchoolText,
    hasLinkedSchoolSource,
    digestReady,
  })

  return {
    hasChildren,
    hasSchoolText,
    hasLinkedSchoolSource,
    hasDiscoveredWebsite,
    hasDiscoveredCalendar,
    hasPendingSchoolSource,
    gmailConnected,
    driveConnected,
    digestReady,
    childStates,
  }
}
