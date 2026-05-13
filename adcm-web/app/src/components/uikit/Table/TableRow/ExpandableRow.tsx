import type React from 'react';
import Collapse from '@uikit/Collapse/Collapse';
import TableRow from '@uikit/Table/TableRow/TableRow';
import cn from 'classnames';
import s from './ExpandableRow.module.scss';
import t from '../Table.module.scss';

export interface ExpandableRowProps extends React.PropsWithChildren {
  isExpanded: boolean;
  expandedContent?: React.ReactNode;
  colSpan: number;
  className?: string;
  isInactive?: boolean;
}

const ExpandableRow = ({
  children,
  isExpanded,
  expandedContent = undefined,
  colSpan,
  className = '',
  isInactive = false,
}: ExpandableRowProps) => {
  const rowClasses = cn(className, s.expandableRowMain, {
    [s.expanded]: isExpanded,
    [s.expandableRowMain_inactive]: isInactive,
    [t.expandedRow]: isExpanded,
  });

  const expandedRowClasses = cn(s.expandableRowContent, t.expandedBlock);

  return (
    <>
      <TableRow isInactive={isInactive} className={rowClasses}>
        {children}
      </TableRow>
      {expandedContent && isExpanded && (
        <tr className={expandedRowClasses}>
          <td colSpan={colSpan}>
            <Collapse isExpanded={true}>
              <div className={s.expandableRow__container}>
                <div className={s.expandableRow__wrapper}>
                  <div className={s.expandableRowContent_wrapper}>{expandedContent}</div>
                </div>
              </div>
            </Collapse>
          </td>
        </tr>
      )}
    </>
  );
};

export default ExpandableRow;
