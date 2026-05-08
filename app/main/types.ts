export type RpcError = {
  code: string
  message: string
  details?: unknown
}

export type RpcResponse<T = unknown> =
  | {
      id: string
      ok: true
      result: T
    }
  | {
      id: string
      ok: false
      error: RpcError
    }

export type RpcEvent = {
  type: 'event'
  event: string
  payload: unknown
}

export type ApiResult<T> =
  | {
      ok: true
      result: T
    }
  | {
      ok: false
      error: RpcError
    }
