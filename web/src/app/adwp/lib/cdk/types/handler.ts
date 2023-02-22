export type AdwpHandler<T, G> = (item: T) => G;
export type AdwpBooleanHandler<T> = AdwpHandler<T, boolean>;
export type AdwpStringHandler<T> = AdwpHandler<T, string>;
