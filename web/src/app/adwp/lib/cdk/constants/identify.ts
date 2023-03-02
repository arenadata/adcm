import { AdwpIdentityMatcher } from '../types';

/**
 * Default method to identify two objects by ids
 */
export const ADWP_IDENTITY_MATCHER: AdwpIdentityMatcher<any> = (item1: any, item2: any) => item1.id === item2.id;
