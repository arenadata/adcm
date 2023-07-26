import React, { useRef } from 'react';
import { Button } from '@uikit';

const HostsCreateHostButton: React.FC = () => {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleClick = () => {
    inputRef.current?.click();
  };

  return (
    <>
      <Button onClick={handleClick}>Create host</Button>
    </>
  );
};

export default HostsCreateHostButton;
