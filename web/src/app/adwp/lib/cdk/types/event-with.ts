export interface AdwpTypedEventTarget<E> {
  addEventListener(
    type: string,
    listener: ((evt: E) => void) | null,
    options?: boolean | AddEventListenerOptions,
  ): void;

  removeEventListener(
    type: string,
    listener?: ((evt: E) => void) | null,
    options?: boolean | EventListenerOptions,
  ): void;
}

export type AdwpEventWith<G extends Event, T extends AdwpTypedEventTarget<G>> = G & {
  readonly currentTarget: T;
};
