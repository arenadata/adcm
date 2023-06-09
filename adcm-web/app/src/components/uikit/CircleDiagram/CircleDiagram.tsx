import React from 'react';
import s from './CircleDiagram.module.scss';
import cn from 'classnames';
import { ReactComponent as Circle } from './circle.svg';

export interface CircleDiagramProps {
  totalCount: number;
  currentCount: number;
  colorClass: string;
}

const dash = 471.1;

const percentToDashPercent = (percent: number) => dash * (1 - percent / 100);

const CircleDiagram = ({ totalCount, currentCount, colorClass }: CircleDiagramProps) => {
  const circleDiagramClasses = cn(s.circleDiagram, colorClass);

  const percents = totalCount >= currentCount ? Math.round((100 * currentCount) / totalCount) : 100;
  const styles = {
    '--dash': dash,
    '--dash-percent': percentToDashPercent(percents),
  } as React.CSSProperties;

  return (
    <div className={circleDiagramClasses} style={styles}>
      <Circle />
      <div className={s.circleDiagram__counter}> {`${currentCount}/${totalCount}`}</div>
    </div>
  );
};

export default CircleDiagram;
