declare const window: Window &
  typeof globalThis & {
    _getEnv_: (v: string) => string;
  };

export const getEnv = (name?: string): string => {
  if (typeof name === 'undefined') return '';
  return import.meta.env[name] || (window && window._getEnv_ && window._getEnv_(name));
};
