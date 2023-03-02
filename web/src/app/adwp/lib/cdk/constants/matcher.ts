/**
 * Default handler for matching stringified version of an item and a search query
 * @param item arbitrary element to match with a string
 * @param search search query
 * @param stringify handler to turn item into a string
 */
import { AdwpHandler } from '../types';
import { ADWP_DEFAULT_STRINGIFY } from './stringify';

export const ADWP_DEFAULT_MATCHER = <T>(
  item: T,
  search: string,
  stringify: AdwpHandler<T, string> = ADWP_DEFAULT_STRINGIFY,
) => stringify(item).toLowerCase().includes(search.toLowerCase());
