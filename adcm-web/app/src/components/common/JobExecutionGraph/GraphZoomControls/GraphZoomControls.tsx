import { Panel, useReactFlow, useViewport } from '@xyflow/react';
import { Icon } from '@uikit';
import type { IconsNames } from '@uikit';
import { FIT_VIEW_PADDING, GRAPH_ICON_SIZE, INITIAL_VIEWPORT, ZOOM_DURATION_MS } from '../layoutConstants';
import s from './GraphZoomControls.module.scss';

const zoomAnimation = { duration: ZOOM_DURATION_MS };

type ZoomControlButtonProps = {
  icon: IconsNames;
  label: string;
  onClick: () => void;
};

const ZoomControlButton = ({ icon, label, onClick }: ZoomControlButtonProps) => (
  <button type="button" className={s.button} title={label} aria-label={label} onClick={onClick}>
    <Icon name={icon} size={GRAPH_ICON_SIZE} />
  </button>
);

const GraphZoomControls = () => {
  const { zoomIn, zoomOut, fitView, setViewport } = useReactFlow();
  const { zoom } = useViewport();
  const zoomPercent = Math.round(zoom * 100);

  const handleZoomIn = () => zoomIn(zoomAnimation);
  const handleZoomOut = () => zoomOut(zoomAnimation);
  const handleFitView = () => fitView({ padding: FIT_VIEW_PADDING, maxZoom: 1, ...zoomAnimation });
  const handleReset = () => setViewport(INITIAL_VIEWPORT, zoomAnimation);

  return (
    <Panel position="top-right" className={s.panel} data-test="job-execution-graph-zoom">
      <div className={s.scale}>{zoomPercent}%</div>
      <div className={s.buttons}>
        <ZoomControlButton icon="g1-zoom-in" label="Zoom in" onClick={handleZoomIn} />
        <ZoomControlButton icon="g1-zoom-out" label="Zoom out" onClick={handleZoomOut} />
        <ZoomControlButton icon="g1-zoom-fit" label="Fit view" onClick={handleFitView} />
        <ZoomControlButton icon="g1-zoom-reset" label="Reset zoom" onClick={handleReset} />
      </div>
    </Panel>
  );
};

export default GraphZoomControls;
