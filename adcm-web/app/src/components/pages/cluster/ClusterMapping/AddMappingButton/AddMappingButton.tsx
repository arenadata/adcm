import { forwardRef } from 'react';
import { Button, ConditionalWrapper } from '@uikit';
import s from './AddMappingButton.module.scss';
import cn from 'classnames';
import Tooltip from '@uikit/Tooltip/Tooltip';

export interface AddMappingButtonProps {
  className?: string;
  label: string;
  onAddClick: () => void;
  isDisabled?: boolean;
  denyAddHostReason?: React.ReactNode;
}

const AddMappingButton = forwardRef<HTMLButtonElement, AddMappingButtonProps>(
  ({ className = '', label, onAddClick, denyAddHostReason, isDisabled = false }: AddMappingButtonProps, ref) => (
    <ConditionalWrapper Component={Tooltip} isWrap={isDisabled} label={denyAddHostReason} placement="top">
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
