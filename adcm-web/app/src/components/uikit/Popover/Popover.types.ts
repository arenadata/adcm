import type React from 'react';
import type { OffsetOptions } from '@floating-ui/react';
import type { Placement } from '@floating-ui/dom';

export type PopoverPanelProps = React.HTMLAttributes<HTMLDivElement>;

export type PopoverWidth = 'min-parent' | 'max-parent' | 'parent';

export interface PopoverOptions {
  placement?: Placement;
  offset?: OffsetOptions;
  dependencyWidth?: PopoverWidth;
}
