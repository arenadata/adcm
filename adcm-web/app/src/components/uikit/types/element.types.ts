import type React from 'react';

export type ChildWithRef = React.ReactElement & { ref?: React.ForwardedRef<HTMLElement> };
