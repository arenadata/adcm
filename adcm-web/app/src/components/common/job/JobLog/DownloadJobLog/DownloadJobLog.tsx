import React from 'react';
import { apiHost } from '@constants';
import { Button } from '@uikit';

interface DownloadJobLogProps {
  jobId: number;
  jobLogId: number;
}

const DownloadJobLog: React.FC<DownloadJobLogProps> = ({ jobId, jobLogId }) => {
  const downloadLink = `${apiHost}/api/v2/jobs/${jobId}/logs/${jobLogId}/download/`;

  return (
    <a href={downloadLink} download="download" target="_blank">
      <Button variant="secondary" children="Download" />
    </a>
  );
};

export default DownloadJobLog;
