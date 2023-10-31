import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { useParams } from 'react-router-dom';
import { useRequestHostProviderConfigurationGroups } from '@pages/HostProviderPage/HostProviderConfigurationGroups/useRequestHostProviderConfigurationGroups';
import { SortParams } from '@models/table';
import { AdcmConfigGroup } from '@models/adcm';
import ConfigGroupsHeader from '@commonComponents/configGroups/ConfigGroupsHeader/ConfigGroupsHeader';
import ConfigGroupsTable from '@commonComponents/configGroups/ConfigGroupsTable/ConfigGroupsTable';
import {
  openCreateDialog,
  openDeleteDialog,
  openMappingDialog,
} from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupActionsSlice';
import { setSortParams } from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupsTableSlice';
import HostProviderConfigGroupDialogs from '@pages/HostProviderPage/HostProviderConfigurationGroups/HostProviderConfigGroupDialogs/HostProviderConfigGroupDialogs';
import HostProviderConfigurationGroupTableFooter from '@pages/HostProviderPage/HostProviderConfigurationGroups/HostProviderConfigurationGroupTableFooter/HostProviderConfigurationConfigTableFooter';

const HostProviderConfigurationGroups: React.FC = () => {
  const dispatch = useDispatch();

  const { hostproviderId: hostproviderIdFromUrl } = useParams();
  const hostProviderId = Number(hostproviderIdFromUrl);

  const { hostProviderConfigGroups, isLoading } = useStore((s) => s.adcm.hostProviderConfigGroups);
  const sortParams = useStore((s) => s.adcm.hostProviderConfigGroupsTable.sortParams);
  useRequestHostProviderConfigurationGroups();

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  const handleCreateConfigGroup = () => {
    dispatch(openCreateDialog());
  };
  const handleDeleteConfigGroup = (configGroup: AdcmConfigGroup) => {
    dispatch(openDeleteDialog(configGroup));
  };

  const handleMappingConfigGroup = (configGroup: AdcmConfigGroup) => {
    dispatch(openMappingDialog(configGroup));
  };

  return (
    <div>
      <ConfigGroupsHeader onCreate={handleCreateConfigGroup} />
      <ConfigGroupsTable
        configGroups={hostProviderConfigGroups}
        isLoading={isLoading}
        sortParams={sortParams}
        onSorting={handleSorting}
        onMapping={handleMappingConfigGroup}
        editUrlPattern={`/hostproviders/${hostProviderId}/configuration-groups/:configGroupId`}
        onDelete={handleDeleteConfigGroup}
      />
      <HostProviderConfigurationGroupTableFooter />

      <HostProviderConfigGroupDialogs />
    </div>
  );
};

export default HostProviderConfigurationGroups;
