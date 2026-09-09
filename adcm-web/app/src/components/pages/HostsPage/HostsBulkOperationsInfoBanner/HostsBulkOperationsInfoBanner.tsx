import type React from 'react';
import { useCallback } from 'react';
import { Button, WarningMessage } from '@uikit';
import { useLocalStorage } from '@hooks';
import s from './HostsBulkOperationsInfoBanner.module.scss';

const STORAGE_KEY = 'hosts-bulk-operations-info-hidden';

const HostsBulkOperationsInfoBanner: React.FC = () => {
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
      Actions execute commands and provider-specific actions on selected hosts. Select hosts with the same provider to
      enable them.
    </WarningMessage>
  );
};

export default HostsBulkOperationsInfoBanner;
