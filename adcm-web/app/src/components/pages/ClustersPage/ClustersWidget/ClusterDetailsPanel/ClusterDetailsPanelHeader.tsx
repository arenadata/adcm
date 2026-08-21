import type React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, IconButton, Badge } from '@uikit';
import type { AdcmCluster } from '@models/adcm';
import { AdcmEntitySystemState } from '@models/adcm';
import { useDispatch } from '@hooks';
import { clusterStatusLabels, getClusterBadgeStatus } from '@pages/ClustersPage/clusterStatusUtils';
import { openClusterRenameDialog } from '@store/adcm/clusters/clustersActionsSlice';
import s from './ClusterDetailsPanel.module.scss';

export interface ClusterDetailsPanelHeaderProps {
  cluster: AdcmCluster;
}

const ClusterDetailsPanelHeader: React.FC<ClusterDetailsPanelHeaderProps> = ({ cluster }) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const status = getClusterBadgeStatus(cluster.status);

  const handleRenameClick = () => {
    dispatch(openClusterRenameDialog(cluster));
  };

  return (
    <div className={s.clusterDetailsPanel__header}>
      <div className={s.clusterDetailsPanel__titleGroup}>
        <h2 className={s.clusterDetailsPanel__title}>{cluster.name}</h2>
        <Badge status={status}>{clusterStatusLabels[cluster.status]}</Badge>
        {cluster.state === AdcmEntitySystemState.Created && (
          <IconButton icon="g1-edit" size={32} title="Rename" onClick={handleRenameClick} />
        )}
      </div>
      <Button variant="secondary" onClick={() => navigate(`/clusters/${cluster.id}/overview`)}>
        Full overview
      </Button>
    </div>
  );
};

export default ClusterDetailsPanelHeader;
