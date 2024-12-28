import type React from 'react';
import cn from 'classnames';
import s from './PaginationButtons.module.scss';

interface PaginationNumButtonProps extends React.PropsWithChildren {
  onClick: () => void;
  selected?: boolean;
}

const PaginationNumButton = ({ onClick, children, selected = false }: PaginationNumButtonProps) => {
  const btnClasses = cn(s.paginationButton, {
    [s.paginationButton_selected]: selected,
  });

  const handleClick = () => {
    !selected && onClick();
  };

  return (
    <button onClick={handleClick} className={btnClasses}>
      {children}
    </button>
  );
};

export default PaginationNumButton;
