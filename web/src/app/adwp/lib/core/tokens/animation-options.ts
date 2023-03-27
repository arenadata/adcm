import { AnimationOptions } from '@angular/animations';
import { inject, InjectionToken } from '@angular/core';
import { ADWP_ANIMATIONS_DURATION } from './animations-duration';

export const ADWP_ANIMATION_OPTIONS = new InjectionToken<AnimationOptions>(
  'Options for Adwp UI animations',
  {
    factory: () => ({
      params: {
        duration: inject(ADWP_ANIMATIONS_DURATION),
      },
    }),
  },
);
