import { matchPath, To } from 'react-router-dom';
export const isCurrentPathname = (pathname: string, to: To, subPattern?: string) => {
  if (matchPath(subPattern || '', pathname)) return true;

  const toString = typeof to === 'string' ? to : to.pathname || '';

  // if `to` - is path of root then full compare with pathname
  if (toString.startsWith('/')) {
    return to === pathname;
  }

  // if `to` - is relative link, check with end of pathname
  return pathname.endsWith(toString);
};
