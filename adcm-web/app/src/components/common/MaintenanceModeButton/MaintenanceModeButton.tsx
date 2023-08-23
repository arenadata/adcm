import React from 'react';
import { IconButton } from '@uikit';
import Tooltip from '@uikit/Tooltip/Tooltip';
import s from './MaintenanceModeButton.module.scss';
import cn from 'classnames';

interface MaintenanceModeButtonProps {
  isMaintenanceModeAvailable: boolean;
  maintenanceModeStatus: string;
  onClick: () => void;
}

const getTooltipLabel = (status: string) => {
  let label = 'Maintenance mode: ';
  switch (status) {
    case 'on':
      label += 'on';
      break;
    case 'off':
      label += 'off';
      break;
    case 'pending':
      label += 'in progress';
      break;
    default:
      label = 'Maintenance mode';
      break;
  }
  return label;
};

const MaintenanceModeButton: React.FC<MaintenanceModeButtonProps> = ({
  maintenanceModeStatus,
  isMaintenanceModeAvailable,
  onClick,
}) => {
  const className = cn(s.maintenanceModeButton, {
    [s.maintenanceModeButton_on]: maintenanceModeStatus === 'on',
    [s.maintenanceModeButton_pending]: maintenanceModeStatus === 'pending',
    [s.maintenanceModeButton_unavailable]: !isMaintenanceModeAvailable,
  });

  return (
    <>
      <Tooltip
        label={isMaintenanceModeAvailable ? getTooltipLabel(maintenanceModeStatus) : 'Maintenance mode: u/a'}
        placement="bottom-start"
      >
        <IconButton icon="g1-maintenance" size={32} onClick={onClick} title="Maintenance mode" className={className} />
      </Tooltip>
    </>
  );
};

export default MaintenanceModeButton;
