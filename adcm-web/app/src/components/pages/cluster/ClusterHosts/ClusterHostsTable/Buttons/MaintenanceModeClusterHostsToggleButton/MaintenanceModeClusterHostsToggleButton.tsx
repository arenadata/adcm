import React from 'react';
import { IconButton, Tooltip } from '@uikit';
import { useDispatch } from '@hooks';
import { AdcmHost } from '@models/adcm';
import s from './MaintenanceModeClusterHostsToggleButton.module.scss';
import cn from 'classnames';
import { openMaintenanceModeDialog } from '@store/adcm/cluster/hosts/hostsActionsSlice';

interface MaintenanceModeClusterHostsProps {
  host: AdcmHost;
}

const MaintenanceModeClusterHostsToggleButton: React.FC<MaintenanceModeClusterHostsProps> = ({ host }) => {
  const dispatch = useDispatch();
  let tooltip = 'Turn maintenance mode on';

  const classes = cn(s.maintenanceModeIcon, {
    [s.maintenanceModeIcon_on]: host.isMaintenanceModeAvailable && host.maintenanceMode === 'on',
    [s.maintenanceModeIcon_unavailable]: !host.isMaintenanceModeAvailable,
  });

  if (host.isMaintenanceModeAvailable) {
    switch (host.maintenanceMode) {
      case 'on':
        tooltip = 'Turn maintenance mode off';
        break;
      case 'off':
        tooltip = 'Turn maintenance mode on';
        break;
      default:
        tooltip = 'Turn maintenance mode on';
    }
  } else {
    tooltip = 'Maintenance mode: u/a';
  }

  const handleMaintenanceModeToggleClick = () => {
    if (!host.isMaintenanceModeAvailable) {
      return;
    }
    dispatch(openMaintenanceModeDialog(host));
  };

  return (
    <>
      <Tooltip label={tooltip}>
        <IconButton
          disabled={!host.isMaintenanceModeAvailable}
          icon="g1-maintenance"
          className={classes}
          size={32}
          onClick={handleMaintenanceModeToggleClick}
        />
      </Tooltip>
    </>
  );
};

export default MaintenanceModeClusterHostsToggleButton;
