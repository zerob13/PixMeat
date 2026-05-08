import { EventEmitter } from 'node:events'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import { app } from 'electron'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'

type EngineProcessEvents = {
  stdoutLine: [line: string]
  stderrLine: [line: string]
  exit: [code: number | null, signal: NodeJS.Signals | null]
}

export class EngineProcess extends EventEmitter {
  private child: ChildProcessWithoutNullStreams | null = null
  private stdoutBuffer = ''
  private stderrBuffer = ''

  start(): void {
    if (this.child && !this.child.killed) {
      return
    }

    const { command, args, cwd } = this.resolveEngineCommand()
    this.child = spawn(command, args, {
      cwd,
      stdio: 'pipe',
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1'
      },
      windowsHide: true
    })

    this.child.stdout.setEncoding('utf8')
    this.child.stderr.setEncoding('utf8')

    this.child.stdout.on('data', (chunk: string) => this.handleStdout(chunk))
    this.child.stderr.on('data', (chunk: string) => this.handleStderr(chunk))
    this.child.on('exit', (code, signal) => {
      this.emit('exit', code, signal)
      this.child = null
    })
  }

  stop(): void {
    if (!this.child || this.child.killed) {
      return
    }
    this.child.kill()
    this.child = null
  }

  restart(): void {
    this.stop()
    this.start()
  }

  sendLine(line: string): void {
    if (!this.child || this.child.killed) {
      this.start()
    }
    if (!this.child?.stdin.writable) {
      throw new Error('Engine process is not writable')
    }
    this.child.stdin.write(`${line}\n`)
  }

  on<K extends keyof EngineProcessEvents>(
    eventName: K,
    listener: (...args: EngineProcessEvents[K]) => void
  ): this {
    return super.on(eventName, listener)
  }

  private resolveEngineCommand(): { command: string; args: string[]; cwd: string } {
    if (process.env.PIXMEAT_ENGINE_COMMAND) {
      return {
        command: process.env.PIXMEAT_ENGINE_COMMAND,
        args: process.env.PIXMEAT_ENGINE_ARGS?.split(' ') ?? [],
        cwd: process.cwd()
      }
    }

    if (app.isPackaged) {
      const exe = process.platform === 'win32' ? 'beauty-engine.exe' : 'beauty-engine'
      const engineRoot = join(process.resourcesPath, 'engine')
      const candidate = join(engineRoot, exe)
      if (existsSync(candidate)) {
        return { command: candidate, args: ['serve'], cwd: engineRoot }
      }
      if (existsSync(join(engineRoot, 'beauty_engine'))) {
        const python = process.env.PIXMEAT_PYTHON ?? (process.platform === 'win32' ? 'python' : 'python3')
        return { command: python, args: ['-m', 'beauty_engine.api'], cwd: engineRoot }
      }
    }

    const python = process.env.PIXMEAT_PYTHON ?? (process.platform === 'win32' ? 'python' : 'python3')
    return {
      command: python,
      args: ['-m', 'beauty_engine.api'],
      cwd: join(process.cwd(), 'engine')
    }
  }

  private handleStdout(chunk: string): void {
    this.stdoutBuffer += chunk
    const lines = this.stdoutBuffer.split(/\r?\n/)
    this.stdoutBuffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.trim()) {
        this.emit('stdoutLine', line)
      }
    }
  }

  private handleStderr(chunk: string): void {
    this.stderrBuffer += chunk
    const lines = this.stderrBuffer.split(/\r?\n/)
    this.stderrBuffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.trim()) {
        this.emit('stderrLine', line)
      }
    }
  }
}
