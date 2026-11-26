import type { AdcmHostShortView, AdcmMapping, AdcmMappingComponent, NotAddedServicesDictionary } from '@models/adcm';
import { arrayToHash } from '@utils/arrayUtils';
import { buildMappingModel } from './buildMappingModel';
import { computeMappingAvailability } from './mappingAvailability';
import type {
  ComponentHostRelations,
  ComponentsMappingErrors,
  MappingAvailability,
  MappingModel,
} from './mapping.types';
import { validate } from './mappingValidate';

export type BuildMappingCoreResult = {
  model: MappingModel;
  mappingErrors: ComponentsMappingErrors;
  availability: MappingAvailability;
  relations: ComponentHostRelations;
};

export const buildMappingCore = (
  currentPairs: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
  notAddedServicesDictionary: NotAddedServicesDictionary,
  relations: ComponentHostRelations,
): BuildMappingCoreResult => {
  const model = buildMappingModel(currentPairs, hosts, components);
  const availability = computeMappingAvailability(model, relations);

  const servicesMappingDictionary = arrayToHash(
    model.servicesMapping,
    (serviceMapping) => serviceMapping.service.prototype.id,
  );
  const mappingErrors = validate(model.componentsMapping, {
    servicesMappingDictionary,
    notAddedServicesDictionary,
    allHostsCount: hosts.length,
  });

  for (const serviceMapping of model.servicesMapping) {
    serviceMapping.hasErrors = serviceMapping.componentsMapping.some(
      (componentMapping) => !!mappingErrors[componentMapping.component.id],
    );
  }

  return {
    model,
    mappingErrors,
    availability,
    relations,
  };
};
