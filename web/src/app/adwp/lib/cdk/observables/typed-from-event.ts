import { fromEvent, Observable } from 'rxjs';
import { AdwpEventWith, AdwpTypedEventTarget } from '../types';

export function typedFromEvent<E extends keyof WindowEventMap>(
  target: Window,
  event: E,
  options?: AddEventListenerOptions,
): Observable<AdwpEventWith<WindowEventMap[E], typeof target>>;
export function typedFromEvent<E extends keyof DocumentEventMap>(
  target: Document,
  event: E,
  options?: AddEventListenerOptions,
): Observable<AdwpEventWith<DocumentEventMap[E], typeof target>>;
export function typedFromEvent<T extends Element, E extends keyof HTMLElementEventMap>(
  target: T,
  event: E,
  options?: AddEventListenerOptions,
): Observable<AdwpEventWith<HTMLElementEventMap[E], typeof target>>;
export function typedFromEvent<E extends Event,
  T extends AdwpTypedEventTarget<AdwpEventWith<E, T>>,
  >(
  target: T,
  event: string,
  options?: AddEventListenerOptions,
): Observable<AdwpEventWith<E, T>>;
export function typedFromEvent<E extends Event>(
  target: AdwpTypedEventTarget<E>,
  event: string,
  options?: AddEventListenerOptions,
): Observable<E>;
export function typedFromEvent<E extends Event>(
  target: AdwpTypedEventTarget<E>,
  event: string,
  options: AddEventListenerOptions = {},
): Observable<E> {
  return fromEvent(target, event, options);
}
