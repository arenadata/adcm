import { AdwpStringHandler } from '../types';

/**
 * Default method to turn arbitrary object into string
 */
export const ADWP_DEFAULT_STRINGIFY: AdwpStringHandler<any> = item => String(item);
