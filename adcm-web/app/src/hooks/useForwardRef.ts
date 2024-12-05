import type { ForwardedRef } from 'react';
import { useMemo } from 'react';
import { mergeRefs } from 'react-merge-refs';
import { deleteUndefinedItems } from '@utils/listUtils';

// biome-ignore lint/suspicious/noExplicitAny:
export const useForwardRef = <T>(ref: ForwardedRef<T>, localRef: any = null) => {
  const reference = useMemo(() => mergeRefs<T>(deleteUndefinedItems([ref, localRef])), [ref, localRef]);
  return reference;
};
