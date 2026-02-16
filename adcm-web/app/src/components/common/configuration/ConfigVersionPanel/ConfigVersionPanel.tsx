import type React from 'react';
import ConfigVersionCell from './ConfigVersionCell/ConfigVersionCell';
import s from './ConfigVersionPanel.module.scss';
import { Pagination } from '@uikit';
import type { PaginationParams } from '@models/table';
import type { ConfigVersion, SelectVersionAction } from './ConfigVersionPanel.types';
import { useStore } from '@hooks';

interface ConfigVersionPanelProps {
  paginationParams: PaginationParams;
  totalItems?: number;
  configsVersions: ConfigVersion[];
  onChangePage: (arg: PaginationParams) => void;
  onSelectConfigVersion: (configId: ConfigVersion['id']) => void;
  onSelectAction: (props: SelectVersionAction) => void;
  selectedConfigId: ConfigVersion['id'];
  isShowDraft?: boolean;
  draftDescription?: string;
  onChangeDraftDescription?: (desc: string) => void;
}

const getDraftVersionConfig = (draftDescription: string, username: string): ConfigVersion => ({
  id: 0,
  creationTime: '',
  description: draftDescription,
  isCurrent: false,
  createdBy: username,
});

const ConfigVersionPanel: React.FC<ConfigVersionPanelProps> = ({
  paginationParams,
  totalItems,
  configsVersions,
  onChangePage,
  onSelectConfigVersion,
  onSelectAction,
  selectedConfigId,
  isShowDraft = false,
  draftDescription = '',
}) => {
  const username = useStore((state) => state.auth.username);
  const isConfigurationUpdated = useStore((state) => state.adcm.entityConfiguration.isConfigurationUpdated);

  return (
    <div className={s.configVersionPanel} data-test="configuration-version-container">
      <Pagination
        className={s.configVersionPanel__pagination}
        hidePerPage={true}
        pageData={paginationParams}
        totalItems={totalItems}
        onChangeData={onChangePage}
      />
      <div className={s.configVersionPanel__content} data-test="configuration-version-content">
        {isShowDraft && (
          <ConfigVersionCell
            configVersion={getDraftVersionConfig(draftDescription, username)}
            onSelectConfigVersion={onSelectConfigVersion}
            onSelectAction={onSelectAction}
            isSelected={selectedConfigId === 0}
            isConfigurationUpdated={false}
          />
        )}
        {configsVersions.map((config) => (
          <ConfigVersionCell
            key={config.id}
            configVersion={config}
            onSelectConfigVersion={onSelectConfigVersion}
            onSelectAction={onSelectAction}
            isSelected={selectedConfigId === config.id}
            isConfigurationUpdated={isConfigurationUpdated && config.isCurrent}
          />
        ))}
      </div>
    </div>
  );
};

export default ConfigVersionPanel;
