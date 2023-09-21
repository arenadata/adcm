import { Button } from '@uikit';

const HostProviderDeleteButton = () => {
  const handleClick = () => {
    // setIsOpen(true);
  };

  return (
    <Button iconLeft="g1-delete" variant="secondary" onClick={handleClick}>
      Delete
    </Button>
  );
};

export default HostProviderDeleteButton;
