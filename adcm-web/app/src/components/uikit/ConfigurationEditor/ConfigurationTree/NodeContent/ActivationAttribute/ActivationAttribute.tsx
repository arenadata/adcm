import { Switch } from '@uikit';

export interface ActivationAttributeProps {
  isShown: boolean;
  isAllowChange: boolean;
  isActive: boolean;
  onToggle: (isActivated: boolean) => void;
}

const ActivationAttribute = ({ isShown, isAllowChange, isActive, onToggle }: ActivationAttributeProps) => {
  if (!isShown) {
    return null;
  }

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (isAllowChange) {
      onToggle(event.target.checked);
    }
  };

  return <Switch size="small" isToggled={isActive} onChange={handleChange} disabled={!isAllowChange} />;
};

export default ActivationAttribute;
