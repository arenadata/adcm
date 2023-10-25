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
  const dataTest = isSynchronized ? 'sync-linked' : 'sync-unlinked';
  const dataTestProps = `clickable=${isAllowChange ? 'true' : 'false'}`;

  return <Icon name={iconName} onClick={handleClick} data-test={dataTest} data-test-props={dataTestProps} />;
};

export default SynchronizedAttribute;
