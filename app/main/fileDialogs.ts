import { dialog, type BrowserWindow } from 'electron'

export const openImageDialog = async (
  window: BrowserWindow
): Promise<{ path: string } | null> => {
  const result = await dialog.showOpenDialog(window, {
    title: 'Open portrait image',
    properties: ['openFile'],
    filters: [
      {
        name: 'Images',
        extensions: ['jpg', 'jpeg', 'png', 'webp', 'tif', 'tiff']
      }
    ]
  })
  if (result.canceled || !result.filePaths[0]) {
    return null
  }
  return { path: result.filePaths[0] }
}

export const exportImageDialog = async (
  window: BrowserWindow,
  defaultName: string
): Promise<{ path: string } | null> => {
  const result = await dialog.showSaveDialog(window, {
    title: 'Export retouched image',
    defaultPath: defaultName,
    filters: [
      { name: 'JPEG', extensions: ['jpg', 'jpeg'] },
      { name: 'PNG', extensions: ['png'] },
      { name: 'TIFF', extensions: ['tif', 'tiff'] }
    ]
  })
  if (result.canceled || !result.filePath) {
    return null
  }
  return { path: result.filePath }
}
