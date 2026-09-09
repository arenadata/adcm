import type React from 'react';
import { memo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import cn from 'classnames';
import type { AdcmCluster } from '@models/adcm';
import { Badge, FlexGroup, IconButton } from '@uikit';
import { useStore } from '@hooks';
import ClusterDynamicActionsIcon from '@pages/ClustersPage/ClustersTable/ClusterDynamicActionsIcon/ClusterDynamicActionsIcon';
import { clusterStatusLabels, getClusterBadgeStatus } from '@pages/ClustersPage/clusterStatusUtils';
import { isBlockingConcernPresent } from '@utils/concernUtils';
import { firstUpperCase } from '@utils/stringUtils';
import { capitalizeEdition } from '@pages/ClustersPage/ClustersWidget/ClustersWidget.utils';
import { getContractVersionBadgeStatus } from '@utils/contractVersionUtils';
import ClusterCardMetrics from './ClusterCardMetrics';
import s from './ClusterCard.module.scss';

export interface ClusterCardProps {
  cluster: AdcmCluster;
  isSelected: boolean;
  onSelect: (clusterId: number) => void;
  onUpgrade: (cluster: AdcmCluster) => void;
  onDelete: (cluster: AdcmCluster) => void;
}

const ClusterCard: React.FC<ClusterCardProps> = ({ cluster, isSelected, onSelect, onUpgrade, onDelete }) => {
  const metrics = useStore((state) => state.adcm.clustersMetrics.metricsByClusterId[cluster.id]);
  const isBlocking = isBlockingConcernPresent(cluster.concerns);
  const concernsCount = cluster.concerns.length;
  const edition = capitalizeEdition(cluster.prototype.edition);
  const clusterTitle = cluster.name || cluster.prototype.displayName;
  const clusterStatus = getClusterBadgeStatus(cluster.status);
  const versionBadgeStatus = getContractVersionBadgeStatus(cluster.prototype.contractVersion?.status);

  const handleCardClick = useCallback(() => {
    onSelect(cluster.id);
  }, [cluster.id, onSelect]);

  const handleActionsClick = useCallback((event: React.MouseEvent) => {
    event.stopPropagation();
  }, []);

  return (
    <div
      className={cn(s.clusterCard, {
        [s.clusterCard_selected]: isSelected && !isBlocking,
        [s.clusterCard_selectedBlocking]: isSelected && isBlocking,
        [s.clusterCard_blocking]: isBlocking,
      })}
      onClick={handleCardClick}
      data-test={`cluster-card-${cluster.id}`}
    >
      <div className={s.clusterCard__header}>
        <Link
          to={`/clusters/${cluster.id}`}
          className={cn('text-link', s.clusterCard__title)}
          title={clusterTitle}
          onClick={(event) => event.stopPropagation()}
        >
          {clusterTitle}
        </Link>
        <Badge className={s.clusterCard__status} status={clusterStatus}>
          {clusterStatusLabels[cluster.status]}
        </Badge>
      </div>

      <FlexGroup gap={12} justifyContent="space-between">
        <div className={s.clusterCard__state}>{firstUpperCase(cluster.state)}</div>
        {concernsCount > 0 && (
          <div className={s.clusterCard__concerns}>
            <Badge status={isBlocking ? 'danger' : 'warning'}>
              {concernsCount} {concernsCount === 1 ? 'concern' : 'concerns'}
            </Badge>
          </div>
        )}
      </FlexGroup>

      <div className={s.clusterCard__product}>
        <span className={s.clusterCard__productName}>{cluster.prototype.displayName}</span>
        <Badge
          className={s.clusterCard__version}
          status={versionBadgeStatus}
          truncate
          title={cluster.prototype.version}
        >
          {cluster.prototype.version}
        </Badge>
        {edition && <Badge status="info">{edition}</Badge>}
      </div>

      <ClusterCardMetrics metrics={metrics} />

      <div className={s.clusterCard__description} title={cluster.description || undefined}>
        {cluster.description || ' '}
      </div>

      <div className={s.clusterCard__footer}>
        <div className={s.clusterCard__actions} onClick={handleActionsClick}>
          <ClusterDynamicActionsIcon cluster={cluster} />
          <IconButton
            icon="g1-upgrade"
            size={32}
            disabled={!cluster.isUpgradable || isBlocking}
            onClick={() => onUpgrade(cluster)}
            title={cluster.isUpgradable ? 'Upgrade' : 'No upgrades'}
          />
          <IconButton icon="g1-delete" size={32} onClick={() => onDelete(cluster)} title="Delete" />
        </div>
      </div>
    </div>
  );
};

export default memo(ClusterCard);
