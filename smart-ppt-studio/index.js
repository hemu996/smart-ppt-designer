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
import { readFile } from 'node:fs/promises'
import { inflateRawSync } from 'node:zlib'
import { extname } from 'node:path'

/** Namespaced so it cannot collide with any other plugin's routes. */
const ROUTE = '/smart-ppt-studio/thumb'

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

/** Build the route handler. Kept free of closure state so it is trivially testable. */
function createThumbHandler() {
  return async (req, res) => {
    try {
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

export function apply(ctx) {
  // `webServer` is optional: a headless host has no browser to serve. Access it
  // through reflect.get because a bare property read on an un-injected key
  // throws on the Cordis context proxy rather than returning undefined.
  const webServer = typeof ctx.reflect?.get === 'function' ? ctx.reflect.get('webServer') : ctx.get?.('webServer')
  if (!webServer) return

  const handler = createThumbHandler()
  const register = () => webServer.register({ kind: 'prefix', path: ROUTE, handler })

  if (typeof ctx.effect === 'function') {
    ctx.effect(register, 'smart-ppt-studio: template thumbnail route')
  } else {
    register()
  }
}
