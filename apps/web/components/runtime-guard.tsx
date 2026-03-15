"use client"

import React from "react"

type Props = {
  name: string
  children: React.ReactNode
}

type State = {
  hasError: boolean
}

export class RuntimeGuard extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: unknown) {
    console.error(`[runtime-guard:${this.props.name}] component crashed`, error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-muted-foreground">
          We hit an issue while loading <strong>{this.props.name}</strong>. Try refreshing
          the page.
        </div>
      )
    }
    return this.props.children
  }
}
