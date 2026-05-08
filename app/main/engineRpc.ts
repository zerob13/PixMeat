import { EventEmitter } from 'node:events'
import type { RpcEvent, RpcResponse } from './types'
import { EngineProcess } from './engineProcess'

type PendingRequest = {
  resolve: (value: RpcResponse) => void
  timeout: NodeJS.Timeout
}

export class EngineRpc extends EventEmitter {
  private readonly engineProcess = new EngineProcess()
  private readonly pending = new Map<string, PendingRequest>()
  private requestSeq = 0
  private latestPreviewToken: string | null = null

  constructor() {
    super()
    this.engineProcess.on('stdoutLine', (line) => this.handleLine(line))
    this.engineProcess.on('stderrLine', (line) => {
      this.emit('stderr', line)
    })
    this.engineProcess.on('exit', (code, signal) => {
      this.rejectAll('engine_exited', `Engine exited (${code ?? signal ?? 'unknown'})`)
      this.emit('event', {
        type: 'event',
        event: 'engine_error',
        payload: { code: 'engine_exited', message: `Engine exited (${code ?? signal ?? 'unknown'})` }
      } satisfies RpcEvent)
    })
  }

  start(): void {
    this.engineProcess.start()
  }

  stop(): void {
    this.engineProcess.stop()
  }

  async restart(): Promise<RpcResponse> {
    this.engineProcess.restart()
    return this.request('health', {}, 10_000)
  }

  async request<TParams extends object>(
    method: string,
    params: TParams,
    timeoutMs = 60_000
  ): Promise<RpcResponse> {
    this.start()
    const id = `req_${Date.now()}_${++this.requestSeq}`
    const payload = { id, method, params }

    if (method === 'render_preview') {
      const token = (params as { request_token?: string }).request_token
      if (token) {
        this.latestPreviewToken = token
      }
    }

    const response = await new Promise<RpcResponse>((resolve) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id)
        resolve({
          id,
          ok: false,
          error: { code: 'timeout', message: `${method} timed out after ${timeoutMs}ms` }
        })
      }, timeoutMs)
      this.pending.set(id, { resolve, timeout })
      this.engineProcess.sendLine(JSON.stringify(payload))
    })

    if (
      method === 'render_preview' &&
      response.ok &&
      typeof response.result === 'object' &&
      response.result !== null
    ) {
      const token = (response.result as { request_token?: string }).request_token
      if (token && this.latestPreviewToken && token !== this.latestPreviewToken) {
        return {
          id,
          ok: false,
          error: { code: 'stale_preview', message: 'Ignored stale preview response' }
        }
      }
    }

    return response
  }

  private handleLine(line: string): void {
    let message: RpcResponse | RpcEvent
    try {
      message = JSON.parse(line) as RpcResponse | RpcEvent
    } catch {
      this.emit('stderr', `Non-JSON engine output: ${line}`)
      return
    }

    if (isRpcEvent(message)) {
      this.emit('event', message)
      return
    }

    const pending = this.pending.get(message.id)
    if (!pending) {
      return
    }
    clearTimeout(pending.timeout)
    this.pending.delete(message.id)
    pending.resolve(message)
  }

  private rejectAll(code: string, message: string): void {
    for (const [id, pending] of this.pending.entries()) {
      clearTimeout(pending.timeout)
      pending.resolve({ id, ok: false, error: { code, message } })
    }
    this.pending.clear()
  }
}

const isRpcEvent = (message: RpcResponse | RpcEvent): message is RpcEvent =>
  'type' in message && message.type === 'event'
