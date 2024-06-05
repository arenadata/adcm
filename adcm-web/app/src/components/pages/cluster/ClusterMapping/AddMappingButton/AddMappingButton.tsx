import { forwardRef } from 'react';
import { Button, ConditionalWrapper, Tooltip } from '@uikit';
import s from './AddMappingButton.module.scss';
import cn from 'classnames';

export interface AddMappingButtonProps {
  className?: string;
  label: string;
  isDisabled?: boolean;
  tooltip?: React.ReactNode;
  onClick: () => void;
}

const AddMappingButton = forwardRef<HTMLButtonElement, AddMappingButtonProps>(
  ({ className = '', label, onClick: onAddClick, tooltip, isDisabled = false }: AddMappingButtonProps, ref) => (
    <ConditionalWrapper Component={Tooltip} isWrap={!!tooltip} label={tooltip} placement="top">
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
    </ConditionalWrapper>
  ),
);

export default AddMappingButton;
