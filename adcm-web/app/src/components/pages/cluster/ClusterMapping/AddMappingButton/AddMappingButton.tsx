import { forwardRef } from 'react';
import { Button } from '@uikit';
import s from './AddMappingButton.module.scss';
import cn from 'classnames';

export interface AddMappingButtonProps {
  className?: string;
  label: string;
  onAddClick: () => void;
}

const AddMappingButton = forwardRef<HTMLButtonElement, AddMappingButtonProps>(
  ({ className = '', label, onAddClick }: AddMappingButtonProps, ref) => (
    <Button
      variant="clear"
      className={cn(s.addMappingButton, className)}
      onClick={onAddClick}
      ref={ref}
      iconRight="g1-add"
    >
      {label}
    </Button>
  ),
);

export default AddMappingButton;
