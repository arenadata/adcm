const dataTestRegexp = /[^a-zA-Z\d]/g;

export const textToDataTestValue = (text: string) => {
  return text.toLowerCase().replaceAll(dataTestRegexp, '_');
};
