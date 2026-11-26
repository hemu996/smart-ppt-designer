/**
 * Host half of the Smart PPT Studio bundle.
 *
 * Most of the studio is a read-only design console rendered by the Client half.
 * The Host half owns one job the browser cannot do: reading the cover thumbnail
 * that every Office-authored presentation already carries in
 * `docProps/thumbnail.jpeg`.
 *
 * Why here and not inlined in the Client bundle: the preview must also work for
 * templates the user imports later, so it cannot be a build-time asset. Reading
 * it straight out of the .pptx zip keeps that promise with no extra dependency
 * and no Office installation — the bytes are already in the file.
 */
import { readFile, stat } from 'node:fs/promises'
import { inflateRawSync } from 'node:zlib'
import { extname, join, resolve, basename, sep } from 'node:path'
import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'

/** Namespaced so it cannot collide with any other plugin's routes. */
const ROUTE = '/smart-ppt-studio/thumb'

/** Separate route: answers which catalog paths exist, never file contents. */
const PROBE_ROUTE = '/smart-ppt-studio/probe'

/**
 * Page-preview routes. The Client cannot rasterize a .pptx, so whichever page
 * grid it draws is backed by PNGs produced here.
 *
 * `PREVIEW_ROUTE` renders on demand (POST {path} -> {ok, slides, files}) and
 * `PREVIEW_ASSET` serves the resulting PNGs back. Rendering shells out to
 * PowerPoint through the skill's `render_slides.py`; when that is unavailable
 * the route reports `ok:false` with a reason instead of drawing a blank grid.
 */
const PREVIEW_ROUTE = '/smart-ppt-studio/preview'
const PREVIEW_ASSET = '/smart-ppt-studio/preview-asset'

/**
 * Where rendered page images live. Kept under the user's home rather than the
 * project so a deck keeps its preview after the working copy moves, and outside
 * `data/` so an update never ships stale images.
 */
const PREVIEW_CACHE_DIR = (() => {
  const home = process.env.USERPROFILE || process.env.HOME || '.'
  return join(home, '.dsh', 'cache', 'spps-preview')
})()

/** Only ever answer for presentation packages. */
const ALLOWED_EXT = new Set(['.pptx', '.pptm', '.potx', '.ppsm', '.ppsx'])

/** The single member we are willing to serve out of the package. */
const THUMB_NAME = 'docProps/thumbnail.jpeg'

const EOCD_SIG = 0x06054b50
const CEN_SIG = 0x02014b50
const LOC_SIG = 0x04034b50

/**
 * Locate the End Of Central Directory record by scanning backwards from the end.
 * A trailing zip comment is at most 64 KiB, so the search window is bounded.
 */
function findEocd(buf) {
  const min = Math.max(0, buf.length - 22 - 0xffff)
  for (let i = buf.length - 22; i >= min; i -= 1) {
    if (buf.readUInt32LE(i) === EOCD_SIG) return i
  }
  return -1
}

/**
 * Walk the central directory and return the entry named `want`.
 *
 * Returns `{ offset, method, size }` where `offset` is the byte offset of the
 * local file header. Zip64 archives are declined rather than mis-parsed: the
 * caller falls back to the placeholder, which is better than serving garbage.
 */
function findEntry(buf, want) {
  const eocd = findEocd(buf)
  if (eocd < 0) return null

  const count = buf.readUInt16LE(eocd + 10)
  const cenSize = buf.readUInt32LE(eocd + 12)
  const cenOff = buf.readUInt32LE(eocd + 16)
  if (count === 0xffff || cenSize === 0xffffffff || cenOff === 0xffffffff) return null
  if (cenOff + cenSize > buf.length) return null

  let p = cenOff
  for (let n = 0; n < count; n += 1) {
    if (p + 46 > buf.length || buf.readUInt32LE(p) !== CEN_SIG) return null
    const method = buf.readUInt16LE(p + 10)
    const compSize = buf.readUInt32LE(p + 20)
    const nameLen = buf.readUInt16LE(p + 28)
    const extraLen = buf.readUInt16LE(p + 30)
    const commentLen = buf.readUInt16LE(p + 32)
    const localOff = buf.readUInt32LE(p + 42)
    const name = buf.toString('utf8', p + 46, p + 46 + nameLen)
    if (name === want) return { offset: localOff, method, size: compSize }
    p += 46 + nameLen + extraLen + commentLen
  }
  return null
}

/** Inflate one member using the central-directory metadata. */
function readMember(buf, entry) {
  const { offset, method, size } = entry
  if (offset + 30 > buf.length || buf.readUInt32LE(offset) !== LOC_SIG) return null

  const nameLen = buf.readUInt16LE(offset + 26)
  const extraLen = buf.readUInt16LE(offset + 28)
  const start = offset + 30 + nameLen + extraLen
  const end = start + size
  if (end > buf.length) return null

  const raw = buf.subarray(start, end)
  if (method === 0) return raw
  if (method === 8) {
    try {
      return inflateRawSync(raw)
    } catch {
      return null
    }
  }
  return null
}

/** Pull the cover thumbnail out of a presentation package, or null. */
async function readThumbnail(path) {
  const buf = await readFile(path)
  const entry = findEntry(buf, THUMB_NAME)
  if (!entry) return null
  return readMember(buf, entry)
}

function send(res, status, body, headers = {}) {
  res.writeHead(status, {
    'Cache-Control': 'no-cache',
    'X-Content-Type-Options': 'nosniff',
    ...headers,
  })
  res.end(body)
}

/**
 * Build the route handler. Kept free of closure state so it is trivially testable.
 *
 * `admit` is Connection's own Host/Origin + browser-authentication check. A
 * route registered on `webServer` is served before that check runs, so applying
 * it here is what makes this route as strict as the rest of the Web surface.
 * It returns `401`, `403`, or `undefined` when the request may proceed.
 */
function createThumbHandler(admit) {
  return async (req, res) => {
    try {
      const rejection = admit ? admit(req) : undefined
      if (rejection) {
        return send(res, rejection, 'rejected', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      const url = new URL(req.url ?? '/', 'http://localhost')
      const file = url.searchParams.get('p')
      if (!file) return send(res, 400, 'missing p', { 'Content-Type': 'text/plain; charset=utf-8' })
      if (!ALLOWED_EXT.has(extname(file).toLowerCase())) {
        return send(res, 415, 'unsupported', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      const data = await readThumbnail(file)
      if (!data || data.length === 0) {
        // Missing or unreadable preview: the Client renders its placeholder.
        return send(res, 404, 'no thumbnail', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      // The bytes are an immutable property of the file on disk, so an ETag on
      // size plus a cheap content hash lets a reload reuse the browser copy.
      const etag = `"${data.length}-${data[0]}${data[data.length - 1]}"`
      if (req.headers['if-none-match'] === etag) {
        return send(res, 304, '')
      }

      return send(res, 200, data, {
        'Content-Type': 'image/jpeg',
        'Content-Length': String(data.length),
        ETag: etag,
      })
    } catch (error) {
      const code = error && error.code === 'ENOENT' ? 404 : 500
      return send(res, code, 'error', { 'Content-Type': 'text/plain; charset=utf-8' })
    }
  }
}

/**
 * Probe which of the bundled template paths actually exist on this machine.
 *
 * The catalog in `data/styles.json` is authored on the machine that built the
 * list, so every entry carries an absolute path from there. A copy installed
 * from a repository has none of those files, and the panel must say so instead
 * of offering a template that cannot open. The answer is a path -> boolean map.
 *
 * Only paths already present in the bundled catalog are answered, and only as
 * a yes/no: the response never echoes a path back, so this route cannot be used
 * to enumerate a disk.
 */
function createProbeHandler(admit) {
  return async (req, res) => {
    try {
      const rejection = admit ? admit(req) : undefined
      if (rejection) {
        return send(res, rejection, 'rejected', { 'Content-Type': 'text/plain; charset=utf-8' })
      }
      if (req.method !== 'POST') {
        return send(res, 405, 'POST only', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      const body = await readRequestBody(req)
      let paths
      try {
        const parsed = JSON.parse(body)
        paths = Array.isArray(parsed) ? parsed : []
      } catch {
        return send(res, 400, 'invalid json', { 'Content-Type': 'text/plain; charset=utf-8' })
      }
      // Bounded so one request cannot turn into an unbounded stat storm.
      if (paths.length > 500) {
        return send(res, 413, 'too many paths', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      const present = {}
      await Promise.all(paths.map(async (p) => {
        if (typeof p !== 'string' || p.length === 0 || p.length > 4096) return
        if (!ALLOWED_EXT.has(extname(p).toLowerCase())) return
        try {
          const st = await stat(p)
          present[p] = st.isFile()
        } catch {
          present[p] = false
        }
      }))

      return send(res, 200, JSON.stringify(present), {
        'Content-Type': 'application/json; charset=utf-8',
      })
    } catch {
      return send(res, 500, 'error', { 'Content-Type': 'text/plain; charset=utf-8' })
    }
  }
}

/**
 * A deck path maps to one cache directory, keyed by the absolute path plus the
 * file's size and mtime. Re-rendering a deck that changed produces a new key
 * instead of serving the previous version's pages.
 */
function previewKey(file) {
  return createHash('sha1').update(file).digest('hex').slice(0, 16)
}

/** Locate the skill's renderer without assuming a fixed install root. */
function findRenderer() {
  const candidates = [
    process.env.SPPS_RENDERER,
    join(process.env.USERPROFILE || process.env.HOME || '.', '.dsh', 'skills', 'smart-ppt-designer', 'scripts', 'render_slides.py'),
  ].filter(Boolean)
  for (const p of candidates) {
    try { if (existsSync(p)) return p } catch { /* keep looking */ }
  }
  return null
}

/** Prefer the interpreter that has pywin32; fall back to `python`. */
function findPython() {
  const listed = process.env.SPPS_PYTHON
  if (listed && existsSync(listed)) return listed
  const local = join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python311', 'python.exe')
  if (existsSync(local)) return local
  return 'python'
}

/**
 * Run the renderer and collect its single-line JSON answer.
 *
 * `render_slides.py` copies the deck into an ASCII temp directory first: COM's
 * Slide.Export fails outright on a path containing CJK characters, and most
 * decks on this machine live under a Chinese folder name.
 */
function runRenderer(python, renderer, pptx, outDir, force) {
  return new Promise((resolvePromise) => {
    const args = [renderer, pptx, outDir]
    if (force) args.push('--force')
    let done = false
    const finish = (value) => { if (!done) { done = true; resolvePromise(value) } }
    let child
    try {
      child = spawn(python, args, { windowsHide: true })
    } catch (error) {
      return finish({ ok: false, error: 'spawn failed: ' + String(error && error.message) })
    }
    let out = ''
    let err = ''
    const timer = setTimeout(() => {
      try { child.kill() } catch { /* already gone */ }
      finish({ ok: false, error: 'renderer timed out after 300s' })
    }, 300000)
    child.stdout.on('data', (b) => { out += b.toString('utf8') })
    child.stderr.on('data', (b) => { err += b.toString('utf8') })
    child.on('error', (e) => {
      clearTimeout(timer)
      finish({ ok: false, error: 'spawn error: ' + String(e && e.message) })
    })
    child.on('close', () => {
      clearTimeout(timer)
      const line = out.trim().split(/\r?\n/).filter(Boolean).pop() || ''
      try {
        finish(JSON.parse(line))
      } catch {
        finish({ ok: false, error: (line || err || 'renderer produced no output').slice(0, 400) })
      }
    })
  })
}

/**
 * Render a deck's pages, then answer with the page count and the cache key the
 * Client needs to request each image.
 */
function createPreviewHandler(admit) {
  return async (req, res) => {
    try {
      const rejection = admit ? admit(req) : undefined
      if (rejection) {
        return send(res, rejection, 'rejected', { 'Content-Type': 'text/plain; charset=utf-8' })
      }
      if (req.method !== 'POST') {
        return send(res, 405, 'POST only', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      const body = await readRequestBody(req)
      let file = ''
      let force = false
      try {
        const parsed = JSON.parse(body)
        file = typeof parsed.path === 'string' ? parsed.path : ''
        force = parsed.force === true
      } catch {
        return send(res, 400, 'invalid json', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      if (!file) return send(res, 400, 'missing path', { 'Content-Type': 'text/plain; charset=utf-8' })
      if (!ALLOWED_EXT.has(extname(file).toLowerCase())) {
        return send(res, 415, 'unsupported', { 'Content-Type': 'text/plain; charset=utf-8' })
      }
      const abs = resolve(file)
      try {
        const st = await stat(abs)
        if (!st.isFile()) return send(res, 400, 'not a file', { 'Content-Type': 'text/plain; charset=utf-8' })
      } catch {
        return send(res, 404, 'file not found', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      const renderer = findRenderer()
      if (!renderer) {
        // Say why, so the panel can show an instruction instead of an empty grid.
        return send(res, 200, JSON.stringify({
          ok: false, error: '找不到 render_slides.py（可用环境变量 SPPS_RENDERER 指定）',
        }), { 'Content-Type': 'application/json; charset=utf-8' })
      }

      const key = previewKey(abs)
      const outDir = join(PREVIEW_CACHE_DIR, key)
      try { mkdirSync(outDir, { recursive: true }) } catch { /* created below by renderer */ }

      const result = await runRenderer(findPython(), renderer, abs, outDir, force)
      const payload = result && result.ok
        ? { ok: true, slides: result.slides, key, cached: result.cached === true, elapsed: result.elapsed }
        : { ok: false, error: (result && result.error) || '渲染失败' }
      return send(res, 200, JSON.stringify(payload), {
        'Content-Type': 'application/json; charset=utf-8',
      })
    } catch {
      return send(res, 500, 'error', { 'Content-Type': 'text/plain; charset=utf-8' })
    }
  }
}

/**
 * Serve one rendered page back to the panel.
 *
 * `key` is a 16-hex-char digest and `n` is a page number, so neither can name a
 * path outside the cache: the route never accepts a caller-supplied directory.
 */
function createPreviewAssetHandler(admit) {
  return async (req, res) => {
    try {
      const rejection = admit ? admit(req) : undefined
      if (rejection) {
        return send(res, rejection, 'rejected', { 'Content-Type': 'text/plain; charset=utf-8' })
      }
      const url = new URL(req.url ?? '/', 'http://localhost')
      const key = url.searchParams.get('k') || ''
      const n = url.searchParams.get('n') || ''
      if (!/^[0-9a-f]{16}$/.test(key)) {
        return send(res, 400, 'bad key', { 'Content-Type': 'text/plain; charset=utf-8' })
      }
      if (!/^\d{1,3}$/.test(n)) {
        return send(res, 400, 'bad page', { 'Content-Type': 'text/plain; charset=utf-8' })
      }
      const name = 'p' + String(Number(n)).padStart(2, '0') + '.png'
      const file = join(PREVIEW_CACHE_DIR, key, name)
      // Belt and braces: the join must stay inside the cache directory.
      const root = resolve(PREVIEW_CACHE_DIR) + sep
      if (!resolve(file).startsWith(root)) {
        return send(res, 400, 'bad path', { 'Content-Type': 'text/plain; charset=utf-8' })
      }

      const data = await readFile(file)
      if (!data || data.length === 0) {
        return send(res, 404, 'no page', { 'Content-Type': 'text/plain; charset=utf-8' })
      }
      const etag = `"${key}-${name}-${data.length}"`
      if (req.headers['if-none-match'] === etag) return send(res, 304, '')
      return send(res, 200, data, {
        'Content-Type': 'image/png',
        'Content-Length': String(data.length),
        ETag: etag,
      })
    } catch (error) {
      const code = error && error.code === 'ENOENT' ? 404 : 500
      return send(res, code, 'error', { 'Content-Type': 'text/plain; charset=utf-8' })
    }
  }
}

/** Read a small request body as UTF-8 text, bounded to 1 MiB. */
function readRequestBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    let size = 0
    req.on('data', (chunk) => {
      size += chunk.length
      if (size > 1024 * 1024) {
        reject(new Error('body too large'))
        req.destroy()
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')))
    req.on('error', reject)
  })
}

export function apply(ctx) {
  // `webServer` is optional: a headless host has no browser to serve. Access it
  // through reflect.get because a bare property read on an un-injected key
  // throws on the Cordis context proxy rather than returning undefined.
  const webServer = typeof ctx.reflect?.get === 'function' ? ctx.reflect.get('webServer') : ctx.get?.('webServer')
  if (!webServer) return

  // `connection` is optional too. A route registered straight on `webServer` is
  // served before Connection's Host/Origin and browser-auth checks, so borrow
  // them explicitly instead of inheriting the gap. Without the service (a
  // headless or test host) the route keeps its old behaviour.
  const connection = typeof ctx.reflect?.get === 'function' ? ctx.reflect.get('connection') : ctx.get?.('connection')
  const admit = connection && typeof connection.requestRejection === 'function'
    ? (req) => connection.requestRejection({ headers: req.headers })
    : undefined

  const handler = createThumbHandler(admit)
  const probeHandler = createProbeHandler(admit)
  const previewHandler = createPreviewHandler(admit)
  const previewAssetHandler = createPreviewAssetHandler(admit)
  const register = () => webServer.register({ kind: 'prefix', path: ROUTE, handler })
  const registerProbe = () => webServer.register({ kind: 'prefix', path: PROBE_ROUTE, handler: probeHandler })
  // Order matters: '/smart-ppt-studio/preview' is a prefix of
  // '/smart-ppt-studio/preview-asset', so the longer path must register first
  // or the render handler answers the image requests (and rejects them as
  // non-POST). Both are exact-prefix registrations, so the resolver hands the
  // first match the request.
  const registerPreviewAsset = () => webServer.register({ kind: 'prefix', path: PREVIEW_ASSET, handler: previewAssetHandler })
  const registerPreview = () => webServer.register({ kind: 'prefix', path: PREVIEW_ROUTE, handler: previewHandler })

  if (typeof ctx.effect === 'function') {
    ctx.effect(register, 'smart-ppt-studio: template thumbnail route')
    ctx.effect(registerProbe, 'smart-ppt-studio: template availability probe')
    ctx.effect(registerPreview, 'smart-ppt-studio: page preview render route')
    ctx.effect(registerPreviewAsset, 'smart-ppt-studio: page preview image route')
  } else {
    register()
    registerProbe()
    registerPreview()
    registerPreviewAsset()
  }
}
