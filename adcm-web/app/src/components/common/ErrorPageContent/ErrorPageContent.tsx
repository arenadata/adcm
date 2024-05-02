import React from 'react';
import s from './ErrorPageContent.module.scss';

export interface ErrorPageContentProps {
  errorCode: string;
  children: React.ReactNode;
}

const ErrorPageContent = ({ errorCode, children }: ErrorPageContentProps) => {
  return (
    <div className={s.errorPageContent} data-test={`error-${errorCode}`}>
      <div className={s.errorPageContent__errorCode}>{errorCode}</div>
      {children}
    </div>
  );
};

export default ErrorPageContent;
