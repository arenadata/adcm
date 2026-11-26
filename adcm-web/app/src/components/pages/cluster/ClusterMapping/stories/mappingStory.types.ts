import type { AdcmHostShortView, AdcmMapping, AdcmMappingComponent, NotAddedServicesDictionary } from '@models/adcm';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard';

export type MappingStoryKind =
  | 'component'
  | 'host'
  | 'componentsMode'
  | 'hostsMode'
  | 'layout'
  | 'dialog'
  | 'wizard'
  | 'action';

export type MappingLayoutVariant = 'cluster_az' | 'wizard_editable_first' | 'action_flat';

export type MappingDialogVariant = 'required_objects' | 'license_step';

export type MappingStoryCase = {
  description: string;
  kind: MappingStoryKind;
  pairs: AdcmMapping[];
  components?: AdcmMappingComponent[];
  hosts?: AdcmHostShortView[];
  notAddedServicesDictionary?: NotAddedServicesDictionary;
  focusComponentName?: string;
  focusHostName?: string;
  layout?: MappingLayoutVariant;
  dialog?: MappingDialogVariant;
  rules?: AdcmActionProcessMappingStepRules[];
  hostsPreviewMode?: boolean;
};
