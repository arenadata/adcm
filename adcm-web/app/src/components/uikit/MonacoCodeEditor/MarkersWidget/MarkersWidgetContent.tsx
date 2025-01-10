import { MarkerSeverity } from '../MonacoCodeEditor.types';
import { useMarkersContext } from './MarkersWidget.context';
import s from './MarkersWidgetContent.module.scss';
import cn from 'classnames';

const MarkersWidgetContent = () => {
  const { markers, onClick } = useMarkersContext();

  return (
    <div className={s.markers}>
      Problems:
      {markers.map((marker) => {
        const iconClassName = cn('codicon', {
          'codicon-warning': marker.severity === MarkerSeverity.Warning,
          [s.warningIcon]: marker.severity === MarkerSeverity.Warning,
          'codicon-error': marker.severity === MarkerSeverity.Error,
          [s.errorIcon]: marker.severity === MarkerSeverity.Error,
        });

        const key = `${marker.startLineNumber}_${marker.startColumn}_${marker.message}`;

        const text = `Line: ${marker.startLineNumber}, column: ${marker.startColumn} ${marker.message}`;

        return (
          <div key={key} className={s.marker} onClick={() => onClick(marker)}>
            <div className={iconClassName} />
            <div className={s.markerText}>{text}</div>
          </div>
        );
      })}
    </div>
  );
};

export default MarkersWidgetContent;
