import type { To } from 'react-router-dom';
import { matchPath } from 'react-router-dom';

export const isCurrentPathname = (pathname: string, to: To | string, subPattern?: string): boolean => {
  if (matchPath(subPattern || '', pathname)) return true;

  const convertToString = typeof to === 'string' ? to : to.pathname || '';

  // if `to` - is path of root then full compare with pathname
  if (convertToString.startsWith('/')) {
    return to === pathname;
  }

  // if `to` - is relative link, check with end of pathname
  return pathname.endsWith(convertToString);
};

export const isCurrentParentPage = (pathname: string, subPage: To | string): boolean => {
  const convertToString = typeof subPage === 'string' ? subPage : subPage.pathname || '';
  const [, firstPart] = pathname.split('/');

  if (firstPart) {
    return convertToString === `/${firstPart}`;
  }

  return false;
};
