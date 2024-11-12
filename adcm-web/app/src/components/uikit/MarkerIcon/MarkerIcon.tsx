import type { HTMLAttributes } from 'react';
import React from 'react';
import type { IconProps } from '@uikit/Icon/Icon';
import Icon from '@uikit/Icon/Icon';
import s from './MarkerIcon.module.scss';
import type { MarkerIconType, MarkerSettings, MarkerVariantType } from './MarkerIcon.types';
import cn from 'classnames';

interface MarkerIconProps extends Omit<HTMLAttributes<HTMLButtonElement>, 'type'> {
  type: MarkerIconType;
  variant: MarkerVariantType;
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

const MarkerIcon = React.forwardRef<HTMLSpanElement, MarkerIconProps>(
  ({ type, size = 16, variant, className, ...props }, ref) => {
    const markerSettings = typesSettings[type];
    const classes = cn(className, s.markerIcon, markerSettings.className, s[`markerIcon_${variant}`]);

    return (
      <span className={classes} {...props} ref={ref}>
        <Icon name={markerSettings.icon} size={size} />
      </span>
    );
  },
);

MarkerIcon.displayName = 'MarkerIcon';

export default MarkerIcon;
