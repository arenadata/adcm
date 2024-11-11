import React, { useState } from 'react';
import ConfigVersionPanel from '../ConfigVersionPanel/ConfigVersionPanel';
import type { AdcmConfigShortView } from '@models/adcm';
import type { PaginationParams } from '@models/table';
import { useLocalPagination } from '@hooks';
import type { SelectVersionAction } from '../ConfigVersionPanel/ConfigVersionPanel.types';

interface ConfigurationVersionsProps {
  configVersions: AdcmConfigShortView[];
  selectedConfigId: AdcmConfigShortView['id'] | null;
  setSelectedConfigId: (id: AdcmConfigShortView['id'] | null) => void;
  isShowDraft?: boolean;
  onSelectAction: (props: SelectVersionAction) => void;
}

const ConfigurationVersions: React.FC<ConfigurationVersionsProps> = ({
  configVersions,
  selectedConfigId,
  setSelectedConfigId,
  isShowDraft,
  onSelectAction,
}) => {
  const { paginateConfigVersions, paginationParams, totalItems, onChangePaginationParams } =
    useConfigurationsPagination(configVersions);

  return (
    <ConfigVersionPanel
      totalItems={totalItems}
      paginationParams={paginationParams}
      configsVersions={paginateConfigVersions}
      onChangePage={onChangePaginationParams}
      onSelectAction={onSelectAction}
      selectedConfigId={selectedConfigId}
      onSelectConfigVersion={setSelectedConfigId}
      isShowDraft={isShowDraft}
    />
  );
};
export default ConfigurationVersions;

const useConfigurationsPagination = (configVersions: AdcmConfigShortView[]) => {
  const [paginationParams, setPaginationParams] = useState<PaginationParams>({
    pageNumber: 0,
    perPage: 5,
  });
  const paginateConfigVersions = useLocalPagination({ list: configVersions, paginationParams });

  return {
    paginateConfigVersions,
    paginationParams,
    totalItems: configVersions.length,
    onChangePaginationParams: setPaginationParams,
  };
};
