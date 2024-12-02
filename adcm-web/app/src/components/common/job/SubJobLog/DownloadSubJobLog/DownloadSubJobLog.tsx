import React from 'react';
import { apiHost } from '@constants';
import { Button } from '@uikit';

interface DownloadSubJobLogProps {
  subJobId: number;
  subJobLogId: number;
}

const DownloadSubJobLog: React.FC<DownloadSubJobLogProps> = ({ subJobId, subJobLogId }) => {
  const downloadLink = `${apiHost}/api/v2/jobs/${subJobId}/logs/${subJobLogId}/download/`;

  return (
    <a href={downloadLink} download="download" target="_blank">
      <Button variant="secondary" children="Download" />
    </a>
  );
};

export default DownloadSubJobLog;
