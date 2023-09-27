import { Icon, IconsNames } from '@uikit';

export interface SynchronizedAttributeProps {
  isShown: boolean;
  isAllowChange: boolean;
  isSynchronized: boolean;
  onToggle: (isSynchronized: boolean) => void;
}

const SynchronizedAttribute = ({ isShown, isAllowChange, isSynchronized, onToggle }: SynchronizedAttributeProps) => {
  if (!isShown) {
    return null;
  }

  const handleClick = () => {
    if (isAllowChange) {
      onToggle(!isSynchronized);
    }
  };

  const iconName: IconsNames = isSynchronized ? 'g1-link' : 'g1-unlink';

  return <Icon name={iconName} onClick={handleClick} />;
};

export default SynchronizedAttribute;
