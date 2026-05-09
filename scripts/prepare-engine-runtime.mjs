#!/usr/bin/env node

import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { RuntimeInjector } from 'tiny-runtime-injector'

const execFileAsync = promisify(execFile)
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const engineRoot = join(root, 'engine')
const runtimeRoot = join(engineRoot, 'runtime')
const uvRoot = join(runtimeRoot, 'uv')
const pythonRoot = join(runtimeRoot, 'python')
const venvRoot = join(runtimeRoot, 'venv')
const markerPath = join(runtimeRoot, '.pixmeat-runtime.json')
const requirementsPath = join(engineRoot, 'requirements.txt')
const pyprojectPath = join(engineRoot, 'pyproject.toml')
const devVenvPython =
  process.platform === 'win32'
    ? join(engineRoot, '.venv', 'Scripts', 'python.exe')
    : join(engineRoot, '.venv', 'bin', 'python')
const venvPython =
  process.platform === 'win32'
    ? join(venvRoot, 'Scripts', 'python.exe')
    : join(venvRoot, 'bin', 'python')

const args = new Set(process.argv.slice(2))
const skipIfMissingAlternativeExists = args.has('--if-missing')

if (skipIfMissingAlternativeExists && existsSync(devVenvPython)) {
  console.log(`Engine .venv exists, skipping bundled runtime: ${devVenvPython}`)
  process.exit(0)
}

const uvInjector = new RuntimeInjector({
  type: 'uv',
  version: process.env.PIXMEAT_UV_VERSION,
  targetDir: uvRoot
})
const pythonInjector = new RuntimeInjector({
  type: 'python',
  version: process.env.PIXMEAT_PYTHON_RUNTIME_VERSION,
  targetDir: pythonRoot
})

const fingerprint = createFingerprint(uvInjector.runtimeInfo.version, pythonInjector.runtimeInfo.version)
if (isPrepared(fingerprint)) {
  console.log(`Bundled engine runtime is current: ${venvPython}`)
  process.exit(0)
}

mkdirSync(runtimeRoot, { recursive: true })
await uvInjector.inject()
await pythonInjector.inject()

rmSync(venvRoot, { recursive: true, force: true })
await run(uvInjector.runtimeInfo.executablePath, [
  'venv',
  '--relocatable',
  '--link-mode',
  'copy',
  '--python',
  pythonInjector.runtimeInfo.executablePath,
  venvRoot
])
await run(uvInjector.runtimeInfo.executablePath, [
  'pip',
  'install',
  '--python',
  venvPython,
  '--requirement',
  requirementsPath,
  '--compile-bytecode'
])

writeFileSync(
  markerPath,
  JSON.stringify(
    {
      fingerprint,
      platform: process.platform,
      arch: process.arch,
      uv: uvInjector.runtimeInfo.version,
      python: pythonInjector.runtimeInfo.version,
      generated_at: new Date().toISOString()
    },
    null,
    2
  )
)
console.log(`Prepared bundled engine runtime: ${venvPython}`)

function createFingerprint(uvVersion, pythonVersion) {
  const hash = createHash('sha256')
  hash.update(JSON.stringify({ platform: process.platform, arch: process.arch, uvVersion, pythonVersion }))
  hash.update(readFileSync(requirementsPath))
  hash.update(readFileSync(pyprojectPath))
  hash.update(readFileSync(fileURLToPath(import.meta.url)))
  return hash.digest('hex')
}

function isPrepared(fingerprint) {
  if (!existsSync(venvPython) || !existsSync(markerPath)) {
    return false
  }
  try {
    const marker = JSON.parse(readFileSync(markerPath, 'utf8'))
    return marker.fingerprint === fingerprint
  } catch {
    return false
  }
}

async function run(command, commandArgs) {
  console.log(`$ ${command} ${commandArgs.join(' ')}`)
  const env = {
    ...process.env,
    PYTHONUTF8: '1',
    UV_LINK_MODE: 'copy',
    UV_NO_PROGRESS: '1',
    UV_PYTHON_DOWNLOADS: 'never'
  }
  const { stdout, stderr } = await execFileAsync(command, commandArgs, {
    cwd: engineRoot,
    env,
    maxBuffer: 1024 * 1024 * 20
  })
  if (stdout.trim()) {
    console.log(stdout.trim())
  }
  if (stderr.trim()) {
    console.error(stderr.trim())
  }
}
