import { EMPTY_FUNCTION } from '../constants';

export const adwpAssert = {
  enabled: false,
  get assert(): (assertion: boolean, ...args: any[]) => void {
    return this.enabled
      ? Function.prototype.bind.call(console.assert, console)
      : EMPTY_FUNCTION;
  },
};
