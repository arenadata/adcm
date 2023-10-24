import { Icon, IconsNames } from '@uikit';

export interface SynchronizedAttributeProps {
  isAllowChange: boolean;
  isSynchronized: boolean;
  onToggle: (isSynchronized: boolean) => void;
}

const SynchronizedAttribute = ({ isAllowChange, isSynchronized, onToggle }: SynchronizedAttributeProps) => {
  const handleClick = () => {
    if (isAllowChange) {
      onToggle(!isSynchronized);
    }
  };

  const iconName: IconsNames = isSynchronized ? 'g1-link' : 'g1-unlink';

  return <Icon name={iconName} onClick={handleClick} />;
};

export default SynchronizedAttribute;
