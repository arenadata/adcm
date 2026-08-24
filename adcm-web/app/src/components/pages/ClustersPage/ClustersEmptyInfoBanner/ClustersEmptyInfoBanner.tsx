import type React from 'react';
import { useCallback } from 'react';
import { Button, WarningMessage } from '@uikit';
import { useLocalStorage } from '@hooks';
import s from './ClustersEmptyInfoBanner.module.scss';

const STORAGE_KEY = 'clusters-empty-info-hidden';

const ClustersEmptyInfoBanner: React.FC = () => {
  const [isHidden, setIsHidden] = useLocalStorage<string>({
    key: STORAGE_KEY,
    initData: 'false',
  });

  const handleHide = useCallback(() => {
    setIsHidden('true');
  }, [setIsHidden]);

  if (isHidden === 'true') {
    return null;
  }

  return (
    <WarningMessage
      variant="info"
      className={s.infoBanner}
      action={
        <Button variant="tertiary" className={s.hideButton} onClick={handleHide}>
          Don&apos;t show again
        </Button>
      }
    >
      You don&apos;t have any clusters yet — create your first cluster to get started.
    </WarningMessage>
  );
};

export default ClustersEmptyInfoBanner;
