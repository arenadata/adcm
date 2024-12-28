import type { IconsNames } from '@uikit/Icon/sprite';

export type MarkerIconType = 'alert' | 'warning' | 'check' | 'info';
export type MarkerVariantType = 'square' | 'round';

type MarkerIcon = Extract<IconsNames, 'marker-alert' | 'marker-check' | 'marker-info'>;

export type MarkerSettings = {
  className: string;
  icon: MarkerIcon;
};
