import { AdcmJobObject, AdcmJobObjectAdvanced, AdcmJobObjectType } from '@models/adcm';
import { linkByObjectTypeMap } from '@pages/JobsPage/JobsTable/JobsTable.constants';

const buildBaseLink = (type: AdcmJobObject['type'], id: number) => {
  return `/${linkByObjectTypeMap[type]}/${id}`;
};
/**
 * TODO: discuss with the backend team the possibility to migrate the logic down below
 */
export const getJobObjectsAdvanced = (objects: AdcmJobObject[]): AdcmJobObjectAdvanced[] => {
  let clusterLink: string;
  let serviceLink: string;
  let componentLink: string;

  return objects.map((object) => {
    const { type, id } = object;
    switch (type) {
      case AdcmJobObjectType.Cluster:
        clusterLink = buildBaseLink(AdcmJobObjectType.Cluster, id);
        return { ...object, link: clusterLink };
      case AdcmJobObjectType.Service:
        serviceLink = clusterLink + buildBaseLink(AdcmJobObjectType.Service, id);
        return { ...object, link: serviceLink };
      case AdcmJobObjectType.Component:
        componentLink = serviceLink + buildBaseLink(AdcmJobObjectType.Component, id);
        return { ...object, link: componentLink };
      default:
        return { ...object, link: buildBaseLink(type, id) };
    }
  });
};
