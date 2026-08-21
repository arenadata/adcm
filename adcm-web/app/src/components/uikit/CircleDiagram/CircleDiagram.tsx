import s from './CircleDiagram.module.scss';
import cn from 'classnames';

export type CircleDiagramSize = 'small' | 'medium';

export interface CircleDiagramProps {
  up: number;
  down: number;
  size?: CircleDiagramSize;
}

const CIRCLE_CX = 85;
const CIRCLE_CY = 85;
const CIRCLE_R = 75;
const STROKE_WIDTH = 20;
const CIRCUMFERENCE = 471.1;

const sizeClassMap: Record<CircleDiagramSize, string> = {
  small: s.circleDiagram_size_small,
  medium: s.circleDiagram_size_medium,
};

const CircleDiagram = ({ up, down, size = 'small' }: CircleDiagramProps) => {
  const sum = up + down;
  const isEmpty = sum === 0;
  const upArcLength = isEmpty ? 0 : (up / sum) * CIRCUMFERENCE;
  const downArcLength = isEmpty ? 0 : (down / sum) * CIRCUMFERENCE;

  const circleDiagramClasses = cn(s.circleDiagram, sizeClassMap[size]);

  return (
    <div className={circleDiagramClasses}>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 170" fill="none" aria-hidden>
        {isEmpty ? (
          <circle
            cx={CIRCLE_CX}
            cy={CIRCLE_CY}
            r={CIRCLE_R}
            stroke="var(--circle-diagram-empty-stroke)"
            strokeWidth={STROKE_WIDTH}
            fill="none"
          />
        ) : (
          <>
            <circle
              cx={CIRCLE_CX}
              cy={CIRCLE_CY}
              r={CIRCLE_R}
              className={s.circleDiagram__segment}
              stroke="var(--circle-diagram-up-color)"
              strokeWidth={STROKE_WIDTH}
              fill="none"
              strokeDasharray={`${upArcLength} ${CIRCUMFERENCE - upArcLength}`}
              strokeDashoffset={0}
              transform={`rotate(-90 ${CIRCLE_CX} ${CIRCLE_CY})`}
            />
            <circle
              cx={CIRCLE_CX}
              cy={CIRCLE_CY}
              r={CIRCLE_R}
              className={s.circleDiagram__segment}
              stroke="var(--circle-diagram-down-color)"
              strokeWidth={STROKE_WIDTH}
              fill="none"
              strokeDasharray={`${downArcLength} ${CIRCUMFERENCE - downArcLength}`}
              strokeDashoffset={-upArcLength}
              transform={`rotate(-90 ${CIRCLE_CX} ${CIRCLE_CY})`}
            />
          </>
        )}
      </svg>
      <div className={s.circleDiagram__counter}>{sum}</div>
    </div>
  );
};

export default CircleDiagram;
