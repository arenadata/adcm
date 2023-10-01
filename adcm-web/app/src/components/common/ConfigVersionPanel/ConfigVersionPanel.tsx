import React from 'react';
import ConfigVersionCell from '@commonComponents/ConfigVersionPanel/ConfigVersionCell/ConfigVersionCell';
import s from './ConfigVersionPanel.module.scss';
import { Pagination, PaginationData } from '@uikit';
import { ConfigVersionPanelProps } from '@commonComponents/ConfigVersionPanel/ConfigVersionPanel.types';
import { defaultPaginationParams } from '@commonComponents/ConfigVersionPanel/ConfigVersionPanel.constants';

const ConfigVersionPanel: React.FC<ConfigVersionPanelProps> = ({
  paginationParams,
  configCellActionsList,
  configs,
  onChangePage,
  onSelectCell,
  onSelectCellAction,
}) => {
  const handlePaginationChange = (params: PaginationData) => {
    onChangePage(params);
  };

  return (
    <div className={s.configVersionPanel__body}>
      <Pagination
        className={s.pagination}
        hidePerPage={true}
        pageData={paginationParams || defaultPaginationParams}
        totalItems={configs.length}
        onChangeData={handlePaginationChange}
      />
      <div className={s.configVersionPanel__content}>
        {configs.map((cell) => (
          <ConfigVersionCell
            key={cell.id}
            configCellActionsList={configCellActionsList}
            cellInfo={cell}
            onClick={onSelectCell}
            onSelectCellAction={onSelectCellAction}
          />
        ))}
      </div>
    </div>
  );
};

export default ConfigVersionPanel;
