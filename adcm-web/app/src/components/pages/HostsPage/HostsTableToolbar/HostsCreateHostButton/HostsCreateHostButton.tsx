import React, { useRef } from 'react';
import { useStore } from '@hooks';
import { Button } from '@uikit';

const HostsCreateHostButton: React.FC = () => {
  // const dispatch = useDispatch();
  const isUploading = useStore(({ adcm }) => adcm.hosts.isUploading);

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
