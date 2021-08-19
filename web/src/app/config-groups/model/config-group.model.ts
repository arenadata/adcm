import { ApiFlat } from '@app/core/types';

export interface ConfigGroup extends ApiFlat {
  name: string;
  description: string;
  hosts: string;
  config: string;
}
