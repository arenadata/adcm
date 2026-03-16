import { isValidData } from '@utils/checkUtils';

// biome-ignore lint/suspicious/noExplicitAny:
export const required = (value: any) => {
  if (typeof value === 'string') {
    return value.length > 0;
  }
  return isValidData(value);
};

export const isEmailValid = (email: string) => {
  const baseEmailRegex = /^[\w.-]+@[a-z0-9-.]+\.[a-z]{2,}$/i;
  const denyConsecutiveSpecialSymbolsRegex = /^[\W_]|[\W_]{2,}|[\W_]$/;

  if (denyConsecutiveSpecialSymbolsRegex.test(email)) {
    return false;
  }

  return baseEmailRegex.test(email);
};

export const isClusterNameValid = (clusterName: string) => {
  return /^[a-z0-9][a-z0-9._-\s]{0,148}[a-z0-9]$/i.test(clusterName);
};

export const isHostNameValid = (hostName: string) => {
  return /^[a-z0-9]{1}[a-z0-9.-]*$/i.test(hostName);
};

export const isHostProviderNameValid = (hostName: string) => {
  return /^[A-Za-z0-9]{1}[A-Za-z0-9._-\s]*[A-Za-z0-9]{1}$/.test(hostName);
};

interface Named {
  name: string;
}

export const isNameUniq = <T extends Named>(name: string, items: T[]): boolean => {
  return !items.some((item) => item.name === name);
};

export const isWhiteSpaceOnly = (value: string) => {
  return /^\s+$/.test(value);
};
