import type React from 'react';
import { useParams } from 'react-router-dom';
import { useStore } from '@hooks';
import ConfigGroupSingleHeader from '@commonComponents/configGroups/ConfigGroupSingleHeader/ConfigGroupSingleHeader';
import { useHostProviderConfigGroupSingle } from '@pages/HostProviderPage/HostProviderConfigurationGroupSingle/useRequestHostProviderConfigurationGroupSingle';
import HostProviderConfigGroupConfiguration from '@pages/HostProviderPage/HostProviderConfigurationGroupSingle/HostProviderConfigGroupConfiguration/HostProviderConfigGroupConfiguration';
import EditConfigGroupDescriptionDialog from '@commonComponents/configGroups/EditConfigGroupDescriptionDialog/EditConfigGroupDescriptionDialog';

const HostProviderConfigGroupSingle: React.FC = () => {
  const { hostproviderId: hostProviderIdFromUrl } = useParams();
  const hostProviderId = Number(hostProviderIdFromUrl);

  useHostProviderConfigGroupSingle();
  const hostProviderConfigGroup = useStore((s) => s.adcm.hostProviderConfigGroup.hostProviderConfigGroup);

  return (
    <>
      <ConfigGroupSingleHeader
        configGroup={hostProviderConfigGroup}
        returnUrl={`/hostproviders/${hostProviderId}/configuration-groups`}
        entityType="hostprovider"
        entityArgs={{ hostProviderId }}
      />
      <EditConfigGroupDescriptionDialog />
      <HostProviderConfigGroupConfiguration />
    </>
  );
};

export default HostProviderConfigGroupSingle;
