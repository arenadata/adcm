import type { HTMLAttributes } from 'react';
import type React from 'react';

const LeftBarMenu: React.FC<HTMLAttributes<HTMLUListElement>> = ({ className, children }) => {
  return <ul className={className}>{children}</ul>;
};

export default LeftBarMenu;
