import type React from 'react';
import type { IMarker } from '../MonacoCodeEditor.types';
import { MarkersCtx } from './MarkersWidget.context';

export interface MarkersWidgetProps extends React.PropsWithChildren {
  markers: IMarker[];
  onClick: (marker: IMarker) => void;
}

const MarkersWidgetProvider = ({ children, ...value }: MarkersWidgetProps) => {
  return <MarkersCtx.Provider value={value}>{children}</MarkersCtx.Provider>;
};

export default MarkersWidgetProvider;
