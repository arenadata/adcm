import type React from 'react';
import { Button } from '@uikit';
import s from './ConfigVersionCell.module.scss';
import ActionMenu from '@uikit/ActionMenu/ActionMenu';
import { dateToString } from '@utils/date/dateConvertUtils';
import cn from 'classnames';
import type { ConfigVersion, SelectVersionAction } from '../ConfigVersionPanel.types';
import { ConfigVersionAction } from '../ConfigVersionPanel.types';

interface ConfigVersionCellProps {
  configVersion: ConfigVersion;
  onSelectConfigVersion: (configId: ConfigVersion['id']) => void;
  onSelectAction: (props: SelectVersionAction) => void;
  isSelected: boolean;
}

const prepareDate = (value: string) => {
  return dateToString(new Date(value), { toUtc: true });
};

const ConfigVersionCell: React.FC<ConfigVersionCellProps> = ({
  configVersion,
  onSelectAction,
  onSelectConfigVersion,
  isSelected = false,
}) => {
  const actionsOptions = [
    {
      value: ConfigVersionAction.Compare,
      label: 'Compare',
      disabled: isSelected,
    },
  ];

  const handleSelectAction = (action: ConfigVersionAction | null) => {
    action && onSelectAction({ action, configId: configVersion.id });
  };

  const handleSelectCell = () => {
    onSelectConfigVersion(configVersion.id);
  };

  return (
    <div className={cn(s.configVersionCell, { [s.configVersionCell_selected]: isSelected })} onClick={handleSelectCell}>
      <div className={s.configVersionCell__header}>
        <div className={s.configVersionCell__title}>
          {configVersion.isCurrent ? 'current' : ''}
          {configVersion.id === 0 ? 'draft' : ''}
        </div>
        <div onClick={(event) => event.stopPropagation()}>
          <ActionMenu placement="bottom-end" value={null} options={actionsOptions} onChange={handleSelectAction}>
            <Button variant="tertiary" iconLeft="dots" />
          </ActionMenu>
        </div>
      </div>
      <div>{configVersion.creationTime ? prepareDate(configVersion.creationTime) : <>&nbsp;</>}</div>
      <div className={s.configVersionCell__description}>{configVersion.description}</div>
    </div>
  );
};

export default ConfigVersionCell;
