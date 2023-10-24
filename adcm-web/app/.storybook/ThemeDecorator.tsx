import { useEffect } from 'react';

export const withThemeProvider = (Story, context) => {
  useEffect(() => {
    const isDark = context.globals.theme === 'dark';
    document.body.classList.toggle('theme-dark', isDark);
    document.body.classList.toggle('theme-light', !isDark);
  }, [context.globals.theme])
  return (<Story />);
};