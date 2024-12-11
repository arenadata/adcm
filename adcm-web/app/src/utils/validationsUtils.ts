// biome-ignore lint/suspicious/noExplicitAny:
export const required = (value: any) => {
  if (typeof value === 'string') {
    return value.length > 0;
  }
  return true;
};

export const isEmailValid = (email: string) => {
  if (!/^[a-z0-9-_@.]+$/i.test(email)) {
    return false;
  }

  const [username, domain, something] = email.split('@');
  // username@domain@something or username or username@
  if (something || !domain || !username) {
    return false;
  }

  // username@subDomain.domain
  return domain.split('.').filter((d) => d).length > 1;
};

export const isClusterNameValid = (clusterName: string) => {
  return /^[a-z0-9][a-z0-9._-\s]{0,148}[a-z0-9]$/i.test(clusterName);
};

export const isHostNameValid = (hostName: string) => {
  return /^[A-Za-z0-9]{1}[A-Za-z0-9.-]*$/.test(hostName);
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
