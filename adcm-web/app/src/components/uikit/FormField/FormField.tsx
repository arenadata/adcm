import React, { useRef, useState } from 'react';
import cn from 'classnames';
import type { LabeledFieldProps } from '@uikit/LabeledField/LabeledField';
import LabeledField from '@uikit/LabeledField/LabeledField';
import Popover from '@uikit/Popover/Popover';
import FormFieldErrorPanel from './FormFieldErrorPanel/FormFieldErrorPanel';
import FormFieldHint from './FormFieldHint/FormFieldHint';

import s from './FormField.module.scss';

interface FormFieldProps extends LabeledFieldProps {
  children: React.ReactElement<{ hasError?: boolean }>;
  hasError?: boolean;
  error?: string;
}

const FormField: React.FC<FormFieldProps> = ({
  hasError: hasForceError,
  error,
  hint,
  children,
  className,
  onFocus,
  onBlur,
  ...props
}) => {
  const isErrorField = !!error || hasForceError;

  const classes = cn(className, s.formField, {
    'has-error': isErrorField,
  });

  const formFieldRef = useRef(null);
  const [isErrorOpen, setIsErrorOpen] = useState(false);

  const isRealErrorOpen = isErrorOpen && !!error;

  const handleInputFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsErrorOpen(true);
    onFocus?.(e);
  };

  const handleInputBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    // We can catch Blur when click by Popover. Focus of field is loose, but this must not hide field's popover
    if (!isRealErrorOpen) {
      setIsErrorOpen(false);
    }
    onBlur?.(e);
  };

  return (
    <>
      <LabeledField
        //
        {...props}
        className={classes}
        hint={<FormFieldHint description={hint} hasError={isErrorField} />}
        ref={formFieldRef}
        onFocus={handleInputFocus}
        onBlur={handleInputBlur}
      >
        {React.Children.only(
          React.cloneElement(children, {
            ...children.props,
            hasError: isErrorField,
          }),
        )}
        <Popover
          isOpen={isRealErrorOpen}
          onOpenChange={setIsErrorOpen}
          triggerRef={formFieldRef}
          dependencyWidth="min-parent"
          offset={6}
          initialFocus={formFieldRef}
        >
          <FormFieldErrorPanel>{error}</FormFieldErrorPanel>
        </Popover>
      </LabeledField>
    </>
  );
};

export default FormField;
