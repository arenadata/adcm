import { isPresent } from './is-present';

export function fallbackValue<T>(value: T | null | undefined, fallback: T): T {
  return isPresent(value) ? value : fallback;
}
