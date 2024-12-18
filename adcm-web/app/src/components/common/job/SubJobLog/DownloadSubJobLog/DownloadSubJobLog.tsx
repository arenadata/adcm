import type React from 'react';
import { apiHost } from '@constants';
import { IconButton } from '@uikit';
import s from './DownloadSubJobLog.module.scss';

interface DownloadSubJobLogProps {
  subJobId: number;
  subJobLogId: number;
}

const DownloadSubJobLog: React.FC<DownloadSubJobLogProps> = ({ subJobId, subJobLogId }) => {
  const downloadLink = `${apiHost}/api/v2/jobs/${subJobId}/logs/${subJobLogId}/download/`;

  return (
    <a className={s.downloadSubJobLog} href={downloadLink} download="download" target="_blank" rel="noreferrer">
      <IconButton size="small" className={s.iconButton} icon="download" />
    </a>
  );
};

export default DownloadSubJobLog;
