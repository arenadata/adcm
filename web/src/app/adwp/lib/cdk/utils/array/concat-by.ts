import { AdwpIdentityMatcher } from '../../types';
import { ADWP_IDENTITY_MATCHER } from '../../constants';

/**
 * Concat unique elements of two arrays by comparator
 *
 * @param arrA
 * @param arrB
 * @param matcher
 */
export function concatBy<T>(arrA: T[], arrB: T[], matcher: AdwpIdentityMatcher<any> = ADWP_IDENTITY_MATCHER): T[] {
  return arrA.concat(arrB.filter((b) => !arrA.find((a) => matcher(a, b))));
}
