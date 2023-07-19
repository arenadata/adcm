export const capitalizeFirstLetter = (value: string): string =>
  value.slice(0, 1).toUpperCase() + value.slice(1).toLowerCase();

export const getStatusLabel = (status: string) => {
  const words = status.trim().replaceAll('_', ' ');
  return capitalizeFirstLetter(words);
};
