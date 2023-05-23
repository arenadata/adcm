import React from 'react';
import Icon from '../../uikit/Icon/Icon';

const Foo: React.FC = () => {
  const zoom = 999;
  return (
    <div>
      Strange {zoom} <Icon name={'eye'} />
    </div>
  );
};
export default Foo;
