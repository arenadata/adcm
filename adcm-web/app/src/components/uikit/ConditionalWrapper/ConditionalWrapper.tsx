import React from 'react';

type WrapOrEmptyProps<T = object> = React.PropsWithChildren<T> & {
  Component: React.FC<T>;
  isWrap: boolean;
};

const ConditionalWrapper = <T,>({ Component, isWrap, children, ...props }: WrapOrEmptyProps<T>) => {
  if (isWrap) {
    return <Component {...(props as T)}>{children}</Component>;
  }
  return <>{children}</>;
};

export default ConditionalWrapper;
