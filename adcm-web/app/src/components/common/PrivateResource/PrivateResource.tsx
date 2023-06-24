import React from 'react';

const PrivateResource: React.FC<React.PropsWithChildren> = ({ children }) => {
  // TODO: add conditions for filter unauthorized  users

  return <>{children}</>;
};

export default PrivateResource;
