import React from 'react';
import { OffsetOptions } from '@floating-ui/react';
import { Placement } from '@floating-ui/dom';

export type PopoverPanelProps = React.HTMLAttributes<HTMLDivElement>;

export type PopoverWidth = 'min-parent' | 'max-parent' | 'parent';

export interface PopoverOptions {
  placement?: Placement;
  offset?: OffsetOptions;
  dependencyWidth?: PopoverWidth;
}
