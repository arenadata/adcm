export const firstUpperCase = (str: string) => (str[0] ?? '').toUpperCase().concat(str.slice(1));

export const snakeToCamelCase = (name: string) => {
  const [firstPart, ...otherParts] = name.toLowerCase().split('_');

  return firstPart.concat(otherParts.map((part) => firstUpperCase(part)).join(''));
};

export const camelToSnakeCase = (name: string) => name.replace(/([A-Z])/g, '_$1').toLowerCase();
