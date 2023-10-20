import React from 'react';
import { Text } from '@uikit';
import s from './ErrorTextContainer.module.scss';

export interface ErrorPageContentProps {
  errorHeader: string;
  children: React.ReactNode;
}

const ErrorTextContainer = ({ errorHeader, children }: ErrorPageContentProps) => {
  return (
    <div className={s.errorTextContainer}>
      <Text variant="h2" className={s.errorTextContainer__header}>
        {errorHeader}
      </Text>
      <div className={s.errorTextContainer__body}>{children}</div>
    </div>
  );
};

export default ErrorTextContainer;
