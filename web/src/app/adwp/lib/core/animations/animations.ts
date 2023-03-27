import { animate, style, transition, trigger } from '@angular/animations';
import { AdwpDropdownAnimation } from '../enums';

const TRANSITION = '{{duration}}ms ease-in-out';
const DURATION = { params: { duration: 300 } };

export const adwpDropdownAnimation = trigger('adwpDropdownAnimation', [
  transition(
    `* => ${AdwpDropdownAnimation.FadeInTop}`,
    [
      style({ transform: 'translateY(-10px)', opacity: 0 }),
      animate(TRANSITION, style({ transform: 'translateY(0)', opacity: 1 })),
    ],
    DURATION,
  ),
  transition(
    `* => ${AdwpDropdownAnimation.FadeInBottom}`,
    [
      style({ transform: 'translateY(10px)', opacity: 0 }),
      animate(TRANSITION, style({ transform: 'translateY(0)', opacity: 1 })),
    ],
    DURATION,
  ),
  transition(
    `${AdwpDropdownAnimation.FadeInBottom} => *`,
    [
      style({ transform: 'translateY(0)', opacity: 1 }),
      animate(TRANSITION, style({ transform: 'translateY(10px)', opacity: 0 })),
    ],
    DURATION,
  ),
  transition(
    `${AdwpDropdownAnimation.FadeInTop} => *`,
    [
      style({ transform: 'translateY(0)', opacity: 1 }),
      animate(TRANSITION, style({ transform: 'translateY(-10px)', opacity: 0 })),
    ],
    DURATION,
  ),
]);
