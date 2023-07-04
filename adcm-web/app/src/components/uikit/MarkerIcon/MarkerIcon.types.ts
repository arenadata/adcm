import { IconsNames } from '@uikit/Icon/sprite';

export type MarkerIconType = 'alert' | 'check' | 'info';

type MarkerIcon = Extract<IconsNames, 'marker-alert' | 'marker-check' | 'marker-info'>;

export type MarkerSettings = {
  className: string;
  icon: MarkerIcon;
};
