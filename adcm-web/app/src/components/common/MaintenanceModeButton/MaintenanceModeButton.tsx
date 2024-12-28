import type React from 'react';
import { IconButton } from '@uikit';
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
      <IconButton
        icon="g1-maintenance"
        size={32}
        title={isMaintenanceModeAvailable ? getTooltipLabel(maintenanceModeStatus) : 'Maintenance mode: u/a'}
        onClick={onClick}
        className={className}
        tooltipProps={{ placement: 'bottom-start' }}
      />
    </>
  );
};

export default MaintenanceModeButton;
