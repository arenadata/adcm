import React, { HTMLAttributes } from 'react';
import Icon, { IconProps } from '@uikit/Icon/Icon';
import s from './MarkerIcon.module.scss';
import { MarkerIconType, MarkerSettings } from './MarkerIcon.types';
import cn from 'classnames';

interface MarkerIconProps extends Omit<HTMLAttributes<HTMLButtonElement>, 'type'> {
  type: MarkerIconType;
  size?: IconProps['size'];
}

const typesSettings: Record<MarkerIconType, MarkerSettings> = {
  alert: {
    className: s.markerIcon_alert,
    icon: 'marker-alert',
  },
  warning: {
    className: s.markerIcon_warning,
    icon: 'marker-alert',
  },
  check: {
    className: s.markerIcon_check,
    icon: 'marker-check',
  },
  info: {
    className: s.markerIcon_info,
    icon: 'marker-info',
  },
};

const MarkerIcon = React.forwardRef<HTMLButtonElement, MarkerIconProps>(
  ({ type, size = 16, className, ...props }, ref) => {
    const markerSettings = typesSettings[type];
    const classes = cn(className, s.markerIcon, markerSettings.className);

    return (
      <button type="button" className={classes} {...props} ref={ref}>
        <Icon name={markerSettings.icon} size={size} />
      </button>
    );
  },
);

MarkerIcon.displayName = 'MarkerIcon';

export default MarkerIcon;
