import React, { useMemo } from 'react';
import { Button } from '@uikit';
import s from './ConfigVersionCell.module.scss';
import ActionMenu from '@uikit/ActionMenu/ActionMenu';
import { dateToString } from '@utils/date/dateConvertUtils';
import cn from 'classnames';
import { ConfigVersionCellProps } from '@commonComponents/ConfigVersionPanel/ConfigVersionCell/ConfigVersionCell.types';

const ConfigVersionCell: React.FC<ConfigVersionCellProps> = ({
  configCellActionsList,
  cellInfo,
  onClick,
  onSelectCellAction,
}) => {
  const actionsOptions = useMemo(() => {
    return configCellActionsList.map(({ id, displayName }) => ({
      label: displayName,
      value: id,
    }));
  }, [configCellActionsList]);

  const handleSelectAction = (actionId: number | null) => {
    actionId && onSelectCellAction(actionId);
  };

  const handleSelectCell = () => {
    onClick(cellInfo.id);
  };

  return (
    <div
      className={cn(s.configVersionCell__body, { [s.configVersionCell__body_selected]: cellInfo.isCurrent })}
      onClick={handleSelectCell}
    >
      <div className={s.configVersionCell__upperBlock}>
        <div className={cn(s.title, cellInfo.isCurrent ? s.title_selected : '')}>
          {cellInfo.isCurrent ? 'current' : ''}
        </div>
        <div onClick={(event) => event.stopPropagation()}>
          <ActionMenu placement="bottom-end" value={null} options={actionsOptions} onChange={handleSelectAction}>
            <Button variant="secondary" iconLeft="dots" />
          </ActionMenu>
        </div>
      </div>
      <div className={'dateLine'}>{dateToString(new Date(cellInfo.creationTime), { toUtc: true })}</div>
      <div className={'descriptionLine'}>{cellInfo.description}</div>
    </div>
  );
};

export default ConfigVersionCell;
