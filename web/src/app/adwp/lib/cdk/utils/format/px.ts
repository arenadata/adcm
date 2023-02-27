import { adwpAssert } from '../../classes';

export function px(value: number): string {
  adwpAssert.assert(Number.isFinite(value), 'Value must be finite number');

  return `${value}px`;
}
