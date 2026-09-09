import type { BadgeStatus, BaseStatus } from '@uikit';
import { AdcmClusterStatus } from '@models/adcm';

export const clusterStatusLabels: Record<AdcmClusterStatus, string> = {
  [AdcmClusterStatus.Up]: 'Up',
  [AdcmClusterStatus.Down]: 'Down',
};

export const clusterStatusesMap: Record<AdcmClusterStatus, BaseStatus> = {
  [AdcmClusterStatus.Up]: 'done',
  [AdcmClusterStatus.Down]: 'unknown',
};

export const getClusterBadgeStatus = (status: AdcmClusterStatus): BadgeStatus => {
  return status === AdcmClusterStatus.Up ? 'success' : 'info';
};
