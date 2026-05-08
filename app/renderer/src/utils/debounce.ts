export const debounce = <Args extends unknown[]>(
  callback: (...args: Args) => void,
  delayMs: number
): ((...args: Args) => void) & { cancel: () => void } => {
  let handle: number | undefined
  const debounced = (...args: Args): void => {
    if (handle !== undefined) {
      window.clearTimeout(handle)
    }
    handle = window.setTimeout(() => {
      handle = undefined
      callback(...args)
    }, delayMs)
  }
  debounced.cancel = () => {
    if (handle !== undefined) {
      window.clearTimeout(handle)
      handle = undefined
    }
  }
  return debounced
}
