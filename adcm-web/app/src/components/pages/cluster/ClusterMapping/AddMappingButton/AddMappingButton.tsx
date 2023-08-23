import { forwardRef } from 'react';
import { Button } from '@uikit';
import s from './AddMappingButton.module.scss';
import cn from 'classnames';

export interface AddMappingButtonProps {
  className?: string;
  label: string;
  onAddClick: () => void;
  isDisabled?: boolean;
}

const AddMappingButton = forwardRef<HTMLButtonElement, AddMappingButtonProps>(
  ({ className = '', label, onAddClick, isDisabled = false }: AddMappingButtonProps, ref) => (
    <Button
      variant="clear"
      className={cn(s.addMappingButton, className)}
      onClick={onAddClick}
      ref={ref}
      iconRight="g1-add"
      disabled={isDisabled}
    >
      {label}
    </Button>
  ),
);

export default AddMappingButton;
