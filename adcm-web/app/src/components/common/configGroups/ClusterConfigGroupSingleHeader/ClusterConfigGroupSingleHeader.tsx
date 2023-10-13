import React from 'react';
import Panel from '@uikit/Panel/Panel';
import { AdcmConfigGroup } from '@models/adcm';
import { Button } from '@uikit';
import { Link } from 'react-router-dom';
import s from './ClusterConfigGroupSingleHeader.module.scss';

interface ClusterConfigGroupSingleHeaderProps {
  configGroup: AdcmConfigGroup | null;
  returnUrl: string;
}

const ClusterConfigGroupSingleHeader: React.FC<ClusterConfigGroupSingleHeaderProps> = ({ configGroup, returnUrl }) => {
  return (
    <Panel className={s.clusterConfigGroupSingleHeader}>
      <strong>{configGroup?.name}</strong>
      <Link to={returnUrl} className="flex-inline">
        <Button variant="secondary">Return back</Button>
      </Link>
    </Panel>
  );
};

export default ClusterConfigGroupSingleHeader;
