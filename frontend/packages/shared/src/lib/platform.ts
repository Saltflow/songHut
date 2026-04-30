export interface PlatformAPI {
  isElectron: boolean;
  isWeb: boolean;
  isMobile: boolean;
  platform: 'electron' | 'web' | 'mobile';
}

function detectPlatform(): PlatformAPI {
  const isElectron = !!(typeof window !== 'undefined' && (window as any).electronAPI);
  const isMobile = /Android|iPhone|iPad|iPod/i.test(
    typeof navigator !== 'undefined' ? navigator.userAgent : ''
  );
  const isWeb = !isElectron && !isMobile;

  return {
    isElectron,
    isWeb,
    isMobile,
    platform: isElectron ? 'electron' : isMobile ? 'mobile' : 'web',
  };
}

export const platform: PlatformAPI = detectPlatform();

export function openFileDialog(accept?: string): Promise<FileList | null> {
  if (platform.isElectron) {
    const api = (window as any).electronAPI;
    return api?.openFileDialog({ accept });
  }
  return new Promise(resolve => {
    const input = document.createElement('input');
    input.type = 'file';
    if (accept) input.accept = accept;
    input.onchange = () => resolve(input.files);
    input.click();
  });
}

export function saveFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
