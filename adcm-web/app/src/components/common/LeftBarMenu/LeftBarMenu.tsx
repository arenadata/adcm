import type { HTMLAttributes } from 'react';
import React from 'react';

const LeftBarMenu: React.FC<HTMLAttributes<HTMLUListElement>> = ({ className, children }) => {
  return <ul className={className}>{children}</ul>;
};

export default LeftBarMenu;
