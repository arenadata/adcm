import type React from 'react';
import { useEffect } from 'react';
import { useDispatch } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';
import { useClusterAnsibleSettings } from './useClusterAnsibleSettings';
import ClusterAnsibleSettingsToolbar from './ClusterAnsibleSettingsToolbar/ClusterAnsibleSettingsToolbar';

const ClusterAnsibleSettings: React.FC = () => {
  const dispatch = useDispatch();
  const {
    //
    cluster,
    selectedConfiguration,
    draftConfiguration,
    setDraftConfiguration,
    onSave,
    onReset,
    isConfigurationLoading,
    accessConfigCheckStatus,
  } = useClusterAnsibleSettings();

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Configuration' },
          { label: 'Ansible settings' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <PermissionsChecker requestState={accessConfigCheckStatus}>
      <ConfigurationFormContextProvider>
        <ClusterAnsibleSettingsToolbar onSave={onSave} onRevert={onReset} isConfigChanged={!!draftConfiguration} />
        <ConfigurationMain
          isLoading={isConfigurationLoading}
          configuration={selectedConfiguration}
          onChangeConfiguration={setDraftConfiguration}
        />
      </ConfigurationFormContextProvider>
    </PermissionsChecker>
  );
};

export default ClusterAnsibleSettings;
