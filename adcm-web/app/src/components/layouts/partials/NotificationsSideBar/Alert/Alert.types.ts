import { HTMLAttributes } from 'react';

export interface AlertOptions extends HTMLAttributes<HTMLDivElement> {
  onClose: () => void;
}
