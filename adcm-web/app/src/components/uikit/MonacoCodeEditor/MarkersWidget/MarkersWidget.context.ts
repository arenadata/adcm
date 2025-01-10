import { createContext, useContext } from 'react';
import type { IMarker } from '../MonacoCodeEditor.types';

type MarkersContextProps = {
  markers: IMarker[];
  onClick: (marker: IMarker) => void;
};

export const MarkersCtx = createContext<MarkersContextProps | null>(null);

export const useMarkersContext = () => {
  const ctx = useContext(MarkersCtx);
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }
  return ctx;
};
