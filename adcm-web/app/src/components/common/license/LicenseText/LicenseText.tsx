import React from 'react';
import s from './LicenseText.module.scss';
import cn from 'classnames';

interface LicenseTextProps {
  children: React.ReactNode;
  className?: string;
}

const LicenseText: React.FC<LicenseTextProps> = ({ className, children }) => {
  return (
    <div className={cn(className, s.licenseText)}>
      <pre>{children}</pre>
    </div>
  );
};

export default LicenseText;
