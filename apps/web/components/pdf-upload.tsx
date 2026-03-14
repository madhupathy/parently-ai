"use client"

import { useState, useCallback } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Upload, FileText, X, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

interface UploadedFile {
  name: string
  status: "uploading" | "done" | "error"
  progress: number
}

export function PdfUpload() {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isDragging, setIsDragging] = useState(false)

  const handleUpload = useCallback(async (fileList: FileList) => {
    const newFiles = Array.from(fileList).filter(
      (f) => f.type === "application/pdf"
    )

    if (newFiles.length === 0) {
      toast.error("Only PDF files are supported")
      return
    }

    for (const file of newFiles) {
      const entry: UploadedFile = {
        name: file.name,
        status: "uploading",
        progress: 0,
      }
      setFiles((prev) => [...prev, entry])

      try {
        const formData = new FormData()
        formData.append("file", file)

        const res = await fetch("/api/uploads/pdf", {
          method: "POST",
          body: formData,
        })

        if (res.ok) {
          setFiles((prev) =>
            prev.map((f) =>
              f.name === file.name
                ? { ...f, status: "done", progress: 100 }
                : f
            )
          )
          toast.success(`${file.name} uploaded successfully`)
        } else {
          setFiles((prev) =>
            prev.map((f) =>
              f.name === file.name ? { ...f, status: "error" } : f
            )
          )
          toast.error(`Failed to upload ${file.name}`)
        }
      } catch {
        setFiles((prev) =>
          prev.map((f) =>
            f.name === file.name ? { ...f, status: "error" } : f
          )
        )
        toast.error(`Network error uploading ${file.name}`)
      }
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      if (e.dataTransfer.files.length > 0) {
        handleUpload(e.dataTransfer.files)
      }
    },
    [handleUpload]
  )

  const removeFile = (name: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== name))
  }

  return (
    <Card className="border-primary/10 shadow-lg shadow-primary/5">
      <CardHeader>
        <div className="flex items-center gap-3">
          <span className="text-2xl">📎</span>
          <div>
            <CardTitle className="text-lg">Upload Documents</CardTitle>
            <CardDescription>
              Drop school PDFs, flyers, and permission slips here.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Drop zone */}
        <div
          className={`relative rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-200 ${
            isDragging
              ? "border-primary bg-primary/5 scale-[1.02]"
              : "border-border/60 hover:border-primary/40 hover:bg-primary/3"
          }`}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-2xl">
            📄
          </div>
          <p className="text-sm font-medium text-foreground">
            Drag & drop PDFs here
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            or click to browse your files
          </p>
          <label className="mt-3 inline-block cursor-pointer">
            <Button variant="outline" size="sm" className="font-semibold" asChild>
              <span>Browse Files</span>
            </Button>
            <input
              type="file"
              accept="application/pdf"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files) handleUpload(e.target.files)
              }}
            />
          </label>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.name}
                className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/30 p-3"
              >
                <span className="text-lg shrink-0">📄</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate">{file.name}</p>
                  {file.status === "uploading" && (
                    <Progress value={file.progress} className="mt-1 h-1.5" />
                  )}
                  {file.status === "done" && (
                    <p className="text-xs text-emerald-600 font-medium">✓ Uploaded</p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0"
                  onClick={() => removeFile(file.name)}
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
