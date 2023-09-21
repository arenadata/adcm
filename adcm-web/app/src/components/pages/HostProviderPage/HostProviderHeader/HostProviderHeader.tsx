import React, { useEffect } from 'react';
import { BaseStatus, Button, ButtonGroup, Statusable } from '@uikit';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import { useDispatch, useStore } from '@hooks';
import { orElseGet } from '@utils/checkUtils';
import HostProviderDeleteButton from './HostProviderDeleteButton/HostProviderDeleteButton';
import s from './HostProviderHeader.module.scss';
import { getHostsCount } from '@store/adcm/hostProviders/hostProviderSlice';

const HostProviderHeader: React.FC = () => {
  const dispatch = useDispatch();

  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);
  const hostsCount = useStore(({ adcm }) => adcm.hostProvider.hostsCount);

  useEffect(() => {
    if (hostProvider) {
      dispatch(getHostsCount(hostProvider.name));
    }
  }, [hostProvider, dispatch]);

  return (
    <EntityHeader
      className={s.hostProviderHeader}
      title={orElseGet(hostProvider, (hostProvider) => (
        <Statusable status={hostProvider.state as BaseStatus}>{hostProvider.name}</Statusable>
      ))}
      central={orElseGet(hostProvider, (hostProvider) => (
        <div className={s.centralWrapper}>
          <span>Version {hostProvider.prototype.version}</span>
          <span>{hostsCount} hosts</span>
        </div>
      ))}
      actions={
        <ButtonGroup>
          <Button iconLeft="g1-actions" variant="secondary">
            Actions
          </Button>
          <Button iconLeft="g1-delete" variant="secondary">
            Delete
          </Button>
          <HostProviderDeleteButton />
        </ButtonGroup>
      }
    />
  );
};

export default HostProviderHeader;
