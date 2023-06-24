import React from 'react';
import { NavLink, To } from 'react-router-dom';
import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';

interface LinkOrEmptyProps extends React.PropsWithChildren {
  to?: To;
}

const LinkOrEmpty: React.FC<LinkOrEmptyProps> = ({ children, to }) => {
  return (
    <ConditionalWrapper Component={NavLink} isWrap={!!to} to={to as To}>
      {children}
    </ConditionalWrapper>
  );
};
export default LinkOrEmpty;
