import type { AdcmConcerns } from './concern';
import type { AdcmEntityState } from './index';
import type { AdcmPrototype } from './prototype';

export interface AdcmSettings {
  id: number;
  name: string;
  state: AdcmEntityState;
  multiState: string[];
  prototype: AdcmPrototype;
  concerns: AdcmConcerns[];
}
