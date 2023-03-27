import {InjectionToken} from '@angular/core';

export const ADWP_ANIMATIONS_DURATION = new InjectionToken<number>(
  'Duration of all Adwp UI animations in ms',
  {
    factory: () => 300,
  },
);
