export const removeUserTableSettings = (username: string) => {
  const keys = Object.keys(window.localStorage);
  for (const key of keys) {
    if (key.startsWith(`${username}_adcm/`) && key.endsWith('Table')) {
      localStorage.removeItem(key);
    }
  }
};
