import { TabsBlock } from '@uikit';
import TabButton from '@uikit/Tabs/TabButton';
import s from './ClusterOverviewFilter.module.scss';
import type { AdcmHostStatus } from '@models/adcm';
import { AdcmServiceStatus } from '@models/adcm';

interface ClusterOverviewFilter {
  status?: AdcmServiceStatus | AdcmHostStatus;
  onStatusChange: (status?: AdcmServiceStatus | AdcmHostStatus) => void;
  dataTest?: string;
}

const ClusterOverviewFilter = ({ status, onStatusChange, dataTest }: ClusterOverviewFilter) => {
  return (
    <TabsBlock variant="secondary" className={s.clusterOverviewFilter} dataTest={dataTest}>
      <TabButton isActive={!status} onClick={() => onStatusChange()}>
        All
      </TabButton>
      <TabButton isActive={status === AdcmServiceStatus.Up} onClick={() => onStatusChange(AdcmServiceStatus.Up)}>
        Up
      </TabButton>
      <TabButton isActive={status === AdcmServiceStatus.Down} onClick={() => onStatusChange(AdcmServiceStatus.Down)}>
        Down
      </TabButton>
    </TabsBlock>
  );
};

export default ClusterOverviewFilter;
