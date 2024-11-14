import type { AxiosResponse } from 'axios';
import { useState } from 'react';

interface DownloadFileProps {
  readonly apiDefinition: () => Promise<AxiosResponse<Blob>>;
  readonly fileName: string;
  readonly preDownloading?: () => void;
  readonly postDownloading?: () => void;
  readonly onError?: () => void;
}

interface DownloadedFileInfo {
  readonly download: () => Promise<void>;
  readonly name: string | undefined;
  readonly url: string | undefined;
}

export const useDownloadFile = ({
  apiDefinition,
  fileName,
  preDownloading,
  postDownloading,
  onError,
}: DownloadFileProps): DownloadedFileInfo => {
  const [url, setFileUrl] = useState<string>();
  const [name, setFileName] = useState<string>();

  const download = async () => {
    try {
      if (preDownloading) {
        preDownloading();
      }

      const response = await apiDefinition();
      setFileName(fileName);

      const link = document.createElement('a');
      link.download = fileName;
      const blob = new Blob([response.data], { type: response.headers['content-type']?.toString() });
      const url = URL.createObjectURL(blob);
      setFileUrl(url);
      link.href = url;
      link.click();
      URL.revokeObjectURL(link.href);

      if (postDownloading) {
        postDownloading();
      }
      URL.revokeObjectURL(url);
    } catch (_error) {
      if (onError) {
        onError();
      }
    }
  };

  return { download, name, url };
};
