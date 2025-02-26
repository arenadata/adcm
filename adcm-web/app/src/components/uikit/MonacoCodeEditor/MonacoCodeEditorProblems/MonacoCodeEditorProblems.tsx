import type { IMarker, IPosition } from '../MonacoCodeEditor.types';
import { MarkerSeverity } from '../MonacoCodeEditor.types';
import cn from 'classnames';
import { useCallback, useMemo, useRef, useState } from 'react';
import Collapse from '@uikit/Collapse/Collapse';
import s from './MonacoCodeEditorProblems.module.scss';
import { useOutsideClick } from '@hooks';

export interface MonacoCodeEditorProblemsProps {
  markers: IMarker[];
  onProblemClick: (position: IPosition) => void;
}

const MonacoCodeEditorProblems = ({ markers, onProblemClick }: MonacoCodeEditorProblemsProps) => {
  const ref = useRef<HTMLDivElement | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const onlyErrorsAndWarnings = useMemo(
    () => markers.filter((m) => m.severity === MarkerSeverity.Warning || m.severity === MarkerSeverity.Error),
    [markers],
  );

  const { errorsCount, warningsCount } = useMemo(() => {
    let errorsCount = 0;
    let warningsCount = 0;
    onlyErrorsAndWarnings.forEach((m) => {
      if (m.severity === MarkerSeverity.Error) {
        errorsCount++;
      } else if (m.severity === MarkerSeverity.Warning) {
        warningsCount++;
      }
    });
    return { errorsCount, warningsCount };
  }, [onlyErrorsAndWarnings]);

  const scrollUpProblems = useCallback(() => {
    setIsExpanded(false);
  }, []);

  useOutsideClick(ref, scrollUpProblems);

  const isShowProblems = errorsCount + warningsCount > 0;

  if (!isShowProblems) return null;

  const handleHeaderClick = () => {
    setIsExpanded((prev) => !prev);
  };

  return (
    <div className={s.monacoCodeEditorProblems} ref={ref}>
      <div className={s.monacoCodeEditorProblems__header} onClick={handleHeaderClick}>
        errors: {errorsCount}, warnings: {warningsCount}
      </div>
      <Collapse isExpanded={isExpanded}>
        <div className={s.monacoCodeEditorProblems__list}>
          {onlyErrorsAndWarnings.map((marker) => {
            const isError = marker.severity === MarkerSeverity.Error;
            const isWarning = marker.severity === MarkerSeverity.Warning;

            const iconClassName = cn('codicon', [s.monacoCodeEditorProblemRecord__icon], {
              'codicon-warning': isWarning,
              [s.monacoCodeEditorProblemRecord__icon_warning]: isWarning,
              'codicon-error': isError,
              [s.monacoCodeEditorProblemRecord__icon_error]: isError,
            });

            const key = `${marker.startLineNumber}_${marker.startColumn}_${marker.message}`;

            return (
              <div
                key={key}
                className={s.monacoCodeEditorProblemRecord}
                onClick={() => onProblemClick({ lineNumber: marker.startLineNumber, column: marker.startColumn })}
              >
                <i className={iconClassName} />
                <div className={s.monacoCodeEditorProblemRecord__description}>
                  <div className={s.monacoCodeEditorProblemRecord__trace}>
                    Line: {marker.startLineNumber}, column: {marker.startColumn}
                  </div>
                  <div className={s.monacoCodeEditorProblemRecord__message}>Message: {marker.message}</div>
                </div>
              </div>
            );
          })}
        </div>
      </Collapse>
    </div>
  );
};

export default MonacoCodeEditorProblems;
