import { cpSync, existsSync, mkdirSync } from "node:fs"
import { join } from "node:path"

const root = process.cwd()
const buildStatic = join(root, ".next", "static")
const standaloneNext = join(root, ".next", "standalone", ".next")
const standaloneStatic = join(standaloneNext, "static")
const publicDir = join(root, "public")
const standalonePublic = join(root, ".next", "standalone", "public")

if (!existsSync(standaloneNext)) {
  throw new Error("Missing .next/standalone/.next. Run `next build` first.")
}

if (!existsSync(buildStatic)) {
  throw new Error("Missing .next/static. Build output is incomplete.")
}

mkdirSync(standaloneNext, { recursive: true })
cpSync(buildStatic, standaloneStatic, { recursive: true, force: true })

if (existsSync(publicDir)) {
  cpSync(publicDir, standalonePublic, { recursive: true, force: true })
}

console.log("[prepare-standalone] copied static/public assets into standalone output")
