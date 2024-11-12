import type { ReactElement } from 'react';
import { createElement } from 'react';
import type { RefractorRoot, RefractorElement, Text } from 'refractor';

export const getParsedCode = (root: RefractorRoot) => {
  return root.children.map((item, id) => createHighlightedElement(item, id.toString()));
};

export const getLines = (code: string) => code.split(/[\r\n]/).map((_, id) => id + 1);

const createHighlightedElement = (item: RefractorElement | Text, id: string): ReactElement | string => {
  if (item.type === 'text') return item.value;

  const element = createElement(item.tagName, { className: getItemClasses(item), key: id }, [
    ...item.children.map((subItem, subId) => createHighlightedElement(subItem, `${id}_${subId}`)),
  ]);

  return element;
};

const getItemClasses = (item: RefractorElement) => {
  if (!item.properties?.className) return '';
  return Array.isArray(item.properties.className) ? item.properties.className.join(' ') : item.properties.className;
};
