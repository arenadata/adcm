import type React from 'react';
import { Tag, IconButton, MarkerIcon, Tooltip, ConditionalWrapper } from '@uikit';
import type { ComponentMappingErrors } from '../../../ClusterMapping.types';
import ComponentRestrictions from '../../RestrictionsList/ComponentRestrictions';
import cn from 'classnames';
import s from './MappedComponent.module.scss';

export interface MappedComponentProps {
  id: number;
  label: string;
  isDisabled?: boolean;
  deleteButtonTooltip?: React.ReactNode;
  mappingErrors?: ComponentMappingErrors;
  onDeleteClick: (e: React.MouseEvent<HTMLButtonElement>) => void;
}

const MappedComponent = ({
  id,
  label,
  isDisabled = false,
  deleteButtonTooltip,
  mappingErrors,
  onDeleteClick,
}: MappedComponentProps) => {
  const isValid = mappingErrors === undefined;
  const className = cn(s.mappingTag, {
    [s.mappingTag_valid]: isValid,
    [s.mappingTag_error]: !isValid,
  });

  return (
    <Tag
      className={className}
      isDisabled={isDisabled}
      endAdornment={
        !isDisabled ? (
          <IconButton
            //
            data-id={id}
            icon="g1-remove"
            variant="primary"
            size={20}
            onClick={onDeleteClick}
            title={deleteButtonTooltip ?? 'Remove'}
            disabled={isDisabled}
          />
        ) : null
      }
    >
      <ConditionalWrapper
        Component={Tooltip}
        isWrap={!isValid}
        label={<ComponentRestrictions errors={mappingErrors!} />}
        placement="bottom-start"
        className={s.mappingTag__tooltip}
        offset={16}
      >
        <MarkerIcon type={isValid ? 'check' : 'alert'} variant="round" />
      </ConditionalWrapper>
      {label}
    </Tag>
  );
};

export default MappedComponent;
