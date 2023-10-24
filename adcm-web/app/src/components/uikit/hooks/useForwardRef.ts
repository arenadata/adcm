import { useMemo, ForwardedRef } from 'react';
import { mergeRefs } from 'react-merge-refs';
import { deleteUndefinedItems } from '@uikit/utils/listUtils';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const useForwardRef = <T>(ref: ForwardedRef<T>, localRef: any = null) => {
  const reference = useMemo(() => mergeRefs<T>(deleteUndefinedItems([ref, localRef])), [ref, localRef]);
  return reference;
};
