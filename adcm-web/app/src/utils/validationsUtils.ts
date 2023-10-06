// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const required = (value: any) => {
  if (typeof value === 'string') {
    return value.length > 0;
  } else if (value == null) {
    return false;
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
  return /^[a-z|A-Z]+(\w|.|-|_|\s)*[a-z|A-Z|0-9]{1}$/.test(clusterName);
};

export const isHostNameValid = (hostName: string) => {
  return /^[A-Za-z0-9]{1}[A-Za-z0-9.-]*$/.test(hostName);
};
