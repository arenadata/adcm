import React from 'react';
import { IconButton } from '@uikit';
import Tooltip from '@uikit/Tooltip/Tooltip';
import s from './MaintenanceModeButton.module.scss';
import cn from 'classnames';
import { AdcmMaintenanceMode } from '@models/adcm';

interface MaintenanceModeButtonProps {
  isMaintenanceModeAvailable: boolean;
  maintenanceModeStatus: string;
  onClick: () => void;
}

const getTooltipLabel = (status: string) => {
  let label = 'Maintenance mode: ';
  switch (status) {
    case AdcmMaintenanceMode.On:
      label += AdcmMaintenanceMode.On;
      break;
    case AdcmMaintenanceMode.Pending:
    case AdcmMaintenanceMode.Changing:
      label += 'in progress';
      break;
    case AdcmMaintenanceMode.Off:
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
    [s.maintenanceModeButton_on]: maintenanceModeStatus === AdcmMaintenanceMode.On,
    [s.maintenanceModeButton_pending]: maintenanceModeStatus === AdcmMaintenanceMode.Pending,
    [s.maintenanceModeButton_changing]: maintenanceModeStatus === AdcmMaintenanceMode.Changing,
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
