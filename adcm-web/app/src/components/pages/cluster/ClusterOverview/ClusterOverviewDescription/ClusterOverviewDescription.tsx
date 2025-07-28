import PageSection from '@commonComponents/PageSection/PageSection';
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
    <>
      <PageSection title="Description">
        <div className={s.clusterOverviewDescription}>
          <span>{cluster?.description || ''}</span>
          <IconButton icon="g1-edit" size={32} onClick={() => handleDescriptionChangeClick(cluster)} />
        </div>
      </PageSection>
    </>
  );
};

export default ClusterOverviewDescription;
