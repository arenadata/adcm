import React from 'react';
import ConfigVersionCell from './ConfigVersionCell/ConfigVersionCell';
import s from './ConfigVersionPanel.module.scss';
import { Pagination } from '@uikit';
import { PaginationParams } from '@models/table';
import { ConfigVersion, SelectVersionAction } from './ConfigVersionPanel.types';

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

const getDraftVersionConfig = (draftDescription: string) => ({
  id: 0,
  creationTime: '',
  description: draftDescription,
  isCurrent: false,
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
  return (
    <div className={s.configVersionPanel}>
      <Pagination
        className={s.configVersionPanel__pagination}
        hidePerPage={true}
        pageData={paginationParams}
        totalItems={totalItems}
        onChangeData={onChangePage}
      />
      <div className={s.configVersionPanel__content}>
        {isShowDraft && (
          <ConfigVersionCell
            configVersion={getDraftVersionConfig(draftDescription)}
            onSelectConfigVersion={onSelectConfigVersion}
            onSelectAction={onSelectAction}
            isSelected={selectedConfigId === 0}
          />
        )}
        {configsVersions.map((config) => (
          <ConfigVersionCell
            key={config.id}
            configVersion={config}
            onSelectConfigVersion={onSelectConfigVersion}
            onSelectAction={onSelectAction}
            isSelected={selectedConfigId === config.id}
          />
        ))}
      </div>
    </div>
  );
};

export default ConfigVersionPanel;
