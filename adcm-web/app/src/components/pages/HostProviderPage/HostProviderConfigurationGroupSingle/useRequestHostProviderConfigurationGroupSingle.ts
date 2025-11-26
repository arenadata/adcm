import { useParams } from 'react-router-dom';
import { useDispatch } from '@hooks';
import { useEffect } from 'react';
import {
  cleanupHostProviderConfigGroup,
  getHostProviderConfigGroup,
} from '@store/adcm/hostProvider/configurationGroupSingle/hostProviderConfigGroupSlice';

export const useHostProviderConfigGroupSingle = () => {
  const { hostproviderId: hostproviderIdFromUrl, configGroupId: configGroupIdFromUrl } = useParams();
  const hostProviderId = Number(hostproviderIdFromUrl);
  const configGroupId = Number(configGroupIdFromUrl);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(getHostProviderConfigGroup({ hostProviderId, configGroupId }));
    return () => {
      dispatch(cleanupHostProviderConfigGroup());
    };
  }, [dispatch, hostProviderId, configGroupId]);
};
