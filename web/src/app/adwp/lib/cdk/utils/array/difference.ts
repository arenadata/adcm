import { AdwpIdentityMatcher } from '../../types';
import { ADWP_IDENTITY_MATCHER } from '../../constants';


/**
 * Difference of two arrays
 *
 * @param arrA
 * @param arrB
 * @param matcher
 */
export function difference<T>(arrA: T[], arrB: T[], matcher: AdwpIdentityMatcher<any> = ADWP_IDENTITY_MATCHER): T[] {
  return arrA.filter(a => !arrB.find((b) => matcher(a, b)));
}
