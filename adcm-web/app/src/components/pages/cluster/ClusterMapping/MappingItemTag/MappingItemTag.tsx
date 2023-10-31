import React from 'react';
import { Tag, IconButton, MarkerIcon, Tooltip, ConditionalWrapper } from '@uikit';
import s from './MappingItemTag.module.scss';
import cn from 'classnames';
import { ValidationResult, ValidationError } from '../ClusterMapping.types';

export interface MappingItemTagProps {
  id: number;
  label: string;
  isDisabled?: boolean;
  validationResult?: ValidationResult;
  onDeleteClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  denyRemoveHostReason?: React.ReactNode;
}

const MappingItemTag = ({
  id,
  label,
  isDisabled = false,
  validationResult,
  onDeleteClick,
  denyRemoveHostReason,
}: MappingItemTagProps) => {
  const className = cn(s.mappingTag, {
    [s['mappingTag_valid']]: validationResult?.isValid === true,
    [s['mappingTag_error']]: validationResult?.isValid === false,
  });

  return (
    <Tag
      className={className}
      isDisabled={isDisabled}
      endAdornment={
        onDeleteClick ? (
          <IconButton
            //
            data-id={id}
            icon="g1-remove"
            variant="secondary"
            size={20}
            onClick={onDeleteClick}
            title={isDisabled ? denyRemoveHostReason : 'Remove'}
            disabled={isDisabled}
          />
        ) : null
      }
    >
      {validationResult !== undefined && (
        <ConditionalWrapper
          Component={Tooltip}
          isWrap={!validationResult.isValid}
          label={(validationResult as ValidationError).errors?.join(', ')}
          placement={'bottom-start'}
          className={s.mappingTag__tooltip}
          offset={16}
        >
          <MarkerIcon type={validationResult.isValid ? 'check' : 'alert'} variant="round" />
        </ConditionalWrapper>
      )}
      {label}
    </Tag>
  );
};

export default MappingItemTag;
