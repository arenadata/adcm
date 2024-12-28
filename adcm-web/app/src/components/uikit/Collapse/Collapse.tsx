import type React from 'react';
import { useCollapse } from 'react-collapsed';

type CollapseProps = React.PropsWithChildren<{
  isExpanded: boolean;
}>;

const Collapse: React.FC<CollapseProps> = ({ isExpanded, children }) => {
  const { getCollapseProps } = useCollapse({ isExpanded });

  return <div {...getCollapseProps()}>{children}</div>;
};

export default Collapse;
