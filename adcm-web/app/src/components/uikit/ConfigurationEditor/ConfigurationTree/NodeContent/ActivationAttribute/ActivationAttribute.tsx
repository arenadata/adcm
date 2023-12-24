import { Switch } from '@uikit';

export interface ActivationAttributeProps {
  isAllowChange: boolean;
  isActive: boolean;
  onToggle: (isActivated: boolean) => void;
}

const ActivationAttribute = ({ isAllowChange, isActive, onToggle }: ActivationAttributeProps) => {
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (isAllowChange) {
      onToggle(event.target.checked);
    }
  };

  return <Switch size="small" isToggled={isActive} onChange={handleChange} disabled={!isAllowChange} />;
};

export default ActivationAttribute;
