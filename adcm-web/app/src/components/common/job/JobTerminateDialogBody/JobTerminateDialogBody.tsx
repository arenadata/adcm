import type React from 'react';
import { WarningMessage } from '@uikit';
import { TERMINATE_RISK_WARNING } from '../jobTerminateDialogContent';
import s from './JobTerminateDialogBody.module.scss';

type JobTerminateDialogBodyProps = {
  description?: string;
};

const JobTerminateDialogBody: React.FC<JobTerminateDialogBodyProps> = ({ description }) => (
  <div className={s.root}>
    {description && <div>{description}</div>}
    <WarningMessage>{TERMINATE_RISK_WARNING}</WarningMessage>
  </div>
);

export default JobTerminateDialogBody;
