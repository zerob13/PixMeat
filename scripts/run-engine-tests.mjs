#!/usr/bin/env node

import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn } from 'node:child_process'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const engineRoot = join(root, 'engine')

let python = findPython()
if (!python) {
  await run(process.execPath, [join(root, 'scripts', 'prepare-engine-runtime.mjs'), '--if-missing'], root)
  python = findPython()
}

if (!python) {
  console.error('No engine Python runtime was found after runtime preparation.')
  process.exit(1)
}

await run(python, ['-m', 'pytest', 'tests'], engineRoot)

function findPython() {
  const candidates =
    process.platform === 'win32'
      ? [
          join(engineRoot, '.venv', 'Scripts', 'python.exe'),
          join(engineRoot, 'runtime', 'venv', 'Scripts', 'python.exe')
        ]
      : [
          join(engineRoot, '.venv', 'bin', 'python'),
          join(engineRoot, 'runtime', 'venv', 'bin', 'python')
        ]
  return candidates.find((candidate) => existsSync(candidate))
}

function run(command, args, cwd) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, {
      cwd,
      env: {
        ...process.env,
        PYTHONNOUSERSITE: '1',
        PYTHONUTF8: '1'
      },
      stdio: 'inherit'
    })
    child.on('error', reject)
    child.on('exit', (code) => {
      if (code === 0) {
        resolvePromise()
      } else {
        reject(new Error(`${command} exited with code ${code ?? 'unknown'}`))
      }
    })
  })
}
