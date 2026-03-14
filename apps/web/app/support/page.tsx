"use client"

import { FormEvent, useState } from "react"

export default function SupportPage() {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setStatus(null)
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, message }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data?.detail || "Unable to send message")
      }
      setStatus("Thanks for reaching out. Our support team will reply soon.")
      setName("")
      setEmail("")
      setMessage("")
    } catch (err: any) {
      setStatus(err?.message || "Unable to send your message right now.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Support</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Need help with Parently? Contact us at support@parently-ai.com or send a message below.
      </p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4 rounded-xl border p-4">
        <div>
          <label className="text-sm font-medium">Name</label>
          <input
            className="mt-1 w-full rounded-md border px-3 py-2"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="text-sm font-medium">Email</label>
          <input
            type="email"
            className="mt-1 w-full rounded-md border px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="text-sm font-medium">Message</label>
          <textarea
            className="mt-1 min-h-32 w-full rounded-md border px-3 py-2"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            required
          />
        </div>
        <button
          type="submit"
          className="rounded-md bg-primary px-4 py-2 text-primary-foreground disabled:opacity-70"
          disabled={loading}
        >
          {loading ? "Sending..." : "Send message"}
        </button>
        {status && <p className="text-sm text-muted-foreground">{status}</p>}
      </form>
    </main>
  )
}
