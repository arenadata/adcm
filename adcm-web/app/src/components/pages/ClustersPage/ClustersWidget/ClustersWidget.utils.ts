import type { AdcmResourceValue } from '@models/adcm';
import { firstUpperCase } from '@utils/stringUtils';

export const formatCpuVcores = (cpuVcores?: number): string => {
  if (cpuVcores === undefined || cpuVcores === null) {
    return '—';
  }

  if (cpuVcores >= 1000) {
    const thousands = Math.floor(cpuVcores / 1000);
    return `${thousands}K+ Core`;
  }

  return `${cpuVcores} Core`;
};

export const formatResourceValue = (resource?: AdcmResourceValue): string => {
  if (!resource) {
    return '—';
  }

  const value = Number.isInteger(resource.value) ? resource.value : Number(resource.value.toFixed(2));
  return `${value} ${resource.unit}`;
};

export const capitalizeEdition = (edition?: string): string => (edition ? firstUpperCase(edition) : '');
