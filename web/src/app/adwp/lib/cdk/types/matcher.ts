import { AdwpStringHandler } from './handler';
import { AdwpMapper } from './mapper';

/**
 * A matcher function to test items against with extra arguments.
 */
export type AdwpMatcher<I> = AdwpMapper<I, boolean>;

export type AdwpStringMatcher<I> = (
  item: I,
  matchValue: string,
  stringify: AdwpStringHandler<I>,
) => boolean;

export type AdwpIdentityMatcher<I> = (item1: I, item2: I) => boolean;
