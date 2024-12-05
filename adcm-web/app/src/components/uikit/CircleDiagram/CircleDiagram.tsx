import type React from 'react';
import s from './CircleDiagram.module.scss';
import cn from 'classnames';
import { ReactComponent as Circle } from './circle.svg';

export interface CircleDiagramProps {
  totalCount: number;
  currentCount: number;
  className?: string;
  isDoubleMode?: boolean;
}

const dash = 471.1;

const percentToDashPercent = (percent: number) => dash * (1 - percent / 100);

const CircleDiagram = ({ totalCount, currentCount, className, isDoubleMode }: CircleDiagramProps) => {
  const circleDiagramClasses = cn(s.circleDiagram, className);

  const percents = isDoubleMode
    ? 100 - Math.round((currentCount / (currentCount + totalCount)) * 100)
    : totalCount >= currentCount
      ? Math.round((100 * currentCount) / totalCount)
      : 100;

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
