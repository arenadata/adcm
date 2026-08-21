import MainInfoPanel from '@commonComponents/MainInfoPanel/MainInfoPanel';
import { Button, ShowMore } from '@uikit';
import {
  FullscreenContainer,
  useFullscreenContext,
} from '@uikit/CodeHighlighter/SubComponents/FullscreenContainer/FullscreenContainer';
import s from './ClusterOverviewBottomBundleInfo.module.scss';

type ClusterOverviewBottomBundleInfoProps = {
  mainInfo?: string;
};

const BundleInfoContent = ({ mainInfo }: ClusterOverviewBottomBundleInfoProps) => {
  const fullscreen = useFullscreenContext();
  const isFullscreen = fullscreen?.isFullscreen ?? false;

  return (
    <>
      <div className={s.clusterOverviewBottomBundleInfo__header}>
        <h3 className={s.clusterOverviewBottomBundleInfo__title}>Bundle info</h3>
        {!isFullscreen && (
          <Button
            iconLeft="g2-expand"
            variant="tertiary"
            title="Full screen"
            onClick={fullscreen?.toggleFullscreen}
            className={s.clusterOverviewBottomBundleInfo__expandBtn}
          />
        )}
      </div>
      {isFullscreen ? (
        <MainInfoPanel mainInfo={mainInfo} />
      ) : (
        <ShowMore maxLines={3}>
          <MainInfoPanel mainInfo={mainInfo} />
        </ShowMore>
      )}
    </>
  );
};

const ClusterOverviewBottomBundleInfo = ({ mainInfo }: ClusterOverviewBottomBundleInfoProps) => (
  <FullscreenContainer className={s.clusterOverviewBottomBundleInfo}>
    <BundleInfoContent mainInfo={mainInfo} />
  </FullscreenContainer>
);

export default ClusterOverviewBottomBundleInfo;
