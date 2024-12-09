import type React from 'react';
import { useStore } from '@hooks';
import ConfigGroupSingleHeader from '@commonComponents/configGroups/ConfigGroupSingleHeader/ConfigGroupSingleHeader';
import { useHostProviderConfigGroupSingle } from '@pages/HostProviderPage/HostProviderConfigurationGroupSingle/useRequestHostProviderConfigurationGroupSingle';
import HostProviderConfigGroupConfiguration from '@pages/HostProviderPage/HostProviderConfigurationGroupSingle/HostProviderConfigGroupConfiguration/HostProviderConfigGroupConfiguration';

const HostProviderConfigGroupSingle: React.FC = () => {
  const hostProvider = useStore((s) => s.adcm.hostProvider.hostProvider);

  useHostProviderConfigGroupSingle();
  const hostProviderConfigGroup = useStore((s) => s.adcm.hostProviderConfigGroup.hostProviderConfigGroup);

  return (
    <>
      <ConfigGroupSingleHeader
        configGroup={hostProviderConfigGroup}
        returnUrl={`/hostproviders/${hostProvider?.id}/configuration-groups`}
      />
      <HostProviderConfigGroupConfiguration />
    </>
  );
};

export default HostProviderConfigGroupSingle;
