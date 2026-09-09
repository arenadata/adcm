import { useStore, useDispatch } from '@hooks';
import { IconButton } from '@uikit';
import type { AdcmCluster } from '@models/adcm';
import { openClusterDescriptionChangeDialog } from '@store/adcm/clusters/clustersActionsSlice';
import s from './ClusterOverviewDescription.module.scss';

const ClusterOverviewDescription = () => {
  const dispatch = useDispatch();
  const { cluster } = useStore((s) => s.adcm.cluster);

  const handleDescriptionChangeClick = (cluster?: AdcmCluster) => {
    if (cluster) {
      dispatch(openClusterDescriptionChangeDialog(cluster));
    }
  };

  return (
    <div className={s.clusterOverviewDescription}>
      <span className={s.clusterOverviewDescription__text}>{cluster?.description || ''}</span>
      <IconButton
        className={s.clusterOverviewDescription__edit}
        icon="g1-edit"
        size={32}
        onClick={() => handleDescriptionChangeClick(cluster)}
        title="Edit description"
      />
    </div>
  );
};

export default ClusterOverviewDescription;
