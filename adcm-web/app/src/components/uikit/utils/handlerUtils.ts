import { ChangeEvent, SyntheticEvent } from 'react';

export const createSyntheticEvent = <T extends Element, E extends Event>(event: E): SyntheticEvent<T> => {
  let isDefaultPrevented = false;
  let isPropagationStopped = false;
  const preventDefault = () => {
    isDefaultPrevented = true;
    event.preventDefault();
  };
  const stopPropagation = () => {
    isPropagationStopped = true;
    event.stopPropagation();
  };
  return {
    nativeEvent: event,
    currentTarget: event.currentTarget as EventTarget & T,
    target: event.target as EventTarget & T,
    bubbles: event.bubbles,
    cancelable: event.cancelable,
    defaultPrevented: event.defaultPrevented,
    eventPhase: event.eventPhase,
    isTrusted: event.isTrusted,
    preventDefault,
    isDefaultPrevented: () => isDefaultPrevented,
    stopPropagation,
    isPropagationStopped: () => isPropagationStopped,
    persist: () => null,
    timeStamp: event.timeStamp,
    type: event.type,
  };
};

export const createChangeEvent = <T extends Element>(target: T | null): ChangeEvent<T> => {
  const event = new Event('change', { bubbles: true });
  Object.defineProperty(event, 'target', { writable: false, value: target });
  return createSyntheticEvent(event) as ChangeEvent<T>;
};
