import React, { useMemo } from 'react';
import cn from 'classnames';
import s from './PaginationButtons.module.scss';
import Icon from '@uikit/Icon/Icon';

export type PaginationBtnArrowVariant = 'arrowSingle' | 'arrowDouble';
export type PaginationBtnVariant = 'next' | 'prev';

interface PaginationButtonProps {
  arrowVariant: PaginationBtnArrowVariant;
  onClick: () => void;
  disabled?: boolean;
  variant?: PaginationBtnVariant;
  dataTest?: string;
}

const getArrowIconName = (arrowVariant: PaginationBtnArrowVariant) =>
  arrowVariant === 'arrowSingle' ? 'chevron' : 'chevron-double';
const getArrowSize = (arrowVariant: PaginationBtnArrowVariant) => (arrowVariant === 'arrowSingle' ? 11 : 20);

const PaginationStepButton = ({
  arrowVariant,
  onClick,
  disabled = false,
  variant = 'prev',
  dataTest = 'pagination-step-button',
}: PaginationButtonProps) => {
  const btnClasses = useMemo(
    () =>
      cn(s.paginationButton, {
        [s[`paginationButtonArrowSingle_${variant}`]]: arrowVariant === 'arrowSingle',
        [s.paginationButtonArrowDouble]: arrowVariant === 'arrowDouble',
      }),
    [variant, arrowVariant],
  );

  return (
    <button onClick={onClick} className={btnClasses} disabled={disabled} data-test={dataTest}>
      <Icon size={getArrowSize(arrowVariant)} name={getArrowIconName(arrowVariant)} />
    </button>
  );
};

export default PaginationStepButton;
