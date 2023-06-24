import React, { HTMLAttributes } from 'react';

const LeftBarMenu: React.FC<HTMLAttributes<HTMLUListElement>> = ({ className, children }) => {
  return <ul className={className}>{children}</ul>;
};

export default LeftBarMenu;
