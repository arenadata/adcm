import PageSection from '@commonComponents/PageSection/PageSection';
import MainInfoPanel from '@commonComponents/MainInfoPanel/MainInfoPanel';
import { useStore } from '@hooks';

const ClusterOverviewInfo = () => {
  const { cluster } = useStore((s) => s.adcm.cluster);

  return (
    <PageSection title="Info">
      <MainInfoPanel mainInfo={cluster?.mainInfo || ''} />
    </PageSection>
  );
};

export default ClusterOverviewInfo;
