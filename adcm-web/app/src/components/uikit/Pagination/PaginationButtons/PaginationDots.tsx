import s from './PaginationButtons.module.scss';
import cn from 'classnames';

interface PaginationDotsProps {
  children: string;
  dotsHandler: () => void;
}

const PaginationDots = ({ children, dotsHandler }: PaginationDotsProps) => {
  return (
    <button className={cn(s.paginationButton, s.paginationButton_dots)} onClick={dotsHandler}>
      {children}
    </button>
  );
};

export default PaginationDots;
