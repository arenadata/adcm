import { adwpAssert } from '../../classes';

/**
 * Checks if the value is in range
 *
 * @param value
 * @param fromInclude lower inclusive limit
 * @param toExclude upper exclusive limit
 */
export function inRange(value: number, fromInclude: number, toExclude: number): boolean {
  adwpAssert.assert(!isNaN(value));
  adwpAssert.assert(!isNaN(fromInclude));
  adwpAssert.assert(!isNaN(toExclude));
  adwpAssert.assert(fromInclude < toExclude);

  return value >= fromInclude && value < toExclude;
}
