import React, { HTMLAttributes } from 'react';
import cn from 'classnames';
import s from './Spinner.module.scss';

const Spinner: React.FC = () => {
  return <div className={s.spinner} />;
};

export default Spinner;

export const SpinnerPanel: React.FC<Omit<HTMLAttributes<HTMLDivElement>, 'children'>> = ({ className, ...props }) => {
  return (
    <div className={cn(s.spinnerPanel, className)} {...props}>
      <Spinner />
    </div>
  );
};
