import { MarkerIconType } from '@uikit';
import { ValidationSummary } from '../ClusterMapping.types';

export const serviceMarkerIcons: Record<ValidationSummary, MarkerIconType> = {
  valid: 'check',
  error: 'alert',
  warning: 'warning',
};
