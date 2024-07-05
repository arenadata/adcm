import React from 'react';
import type { ComponentMappingErrors } from '../../ClusterMapping.types';
import s from './ComponentRestrictions.module.scss';
import cn from 'classnames';

export interface ComponentRestrictionsProps {
  errors: ComponentMappingErrors;
  className?: string;
  onInstallServices?: () => void;
}

const ComponentRestrictions = (props: ComponentRestrictionsProps) => {
  return (
    <ul className={cn(s.componentRestrictions, props.className)}>
      {props.errors.constraintsError && (
        <li className={cn(s.componentRestrictions__listItem, s.componentRestrictions__listItem_constraint)}>
          {props.errors.constraintsError.message}
        </li>
      )}
      {props.errors.dependenciesErrors?.notAddedErrors && (
        <>
          <li className={s.componentRestrictions__listItem}>
            Requires{' '}
            <span className={props.onInstallServices ? 'text-link' : ''} onClick={props.onInstallServices}>
              {' '}
              adding
            </span>{' '}
            of services:
          </li>
          {props.errors.dependenciesErrors.notAddedErrors.map((error) => (
            <li
              key={error.params.service.id}
              className={s.componentRestrictions__listItem}
            >{`- ${error.params.service.displayName}`}</li>
          ))}
        </>
      )}
      {props.errors.dependenciesErrors?.requiredErrors && (
        <>
          <li className={s.componentRestrictions__listItem}>Requires mapping of components:</li>
          {props.errors.dependenciesErrors.requiredErrors.map((error) => (
            <React.Fragment key={error.params.service}>
              {error.params.components.map((name) => (
                <li key={name} className={s.componentRestrictions__listItem}>{`- ${name}`}</li>
              ))}
            </React.Fragment>
          ))}
        </>
      )}
    </ul>
  );
};

export default ComponentRestrictions;
