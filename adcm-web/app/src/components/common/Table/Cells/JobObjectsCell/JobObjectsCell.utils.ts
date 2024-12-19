import type { AdcmJobObject, AdcmJobObjectAdvanced } from '@models/adcm';
import { AdcmJobObjectType } from '@models/adcm';
import { linkByObjectTypeMap } from '@pages/JobsPage/JobsTable/JobsTable.constants';

const buildBaseLink = (type: AdcmJobObject['type'], id?: number) => {
  const baseLink = `/${linkByObjectTypeMap[type]}`;

  return type === AdcmJobObjectType.ActionHostGroup ? baseLink : `${baseLink}/${id}`;
};

/**
 * TODO: discuss with the backend team the possibility to migrate the logic down below
 */
export const getJobObjectsAdvanced = (objects: AdcmJobObject[]): AdcmJobObjectAdvanced[] => {
  const pathToActionHostGroups = buildBaseLink(AdcmJobObjectType.ActionHostGroup);
  let clusterLink: string;
  let serviceLink: string;
  let componentLink: string;
  let actionHostGroupLink: string;

  return objects.map((object) => {
    const { type, id } = object;

    switch (type) {
      case AdcmJobObjectType.Adcm:
        return { ...object, link: '/settings' };
      case AdcmJobObjectType.ActionHostGroup:
        return { ...object, link: actionHostGroupLink };
      case AdcmJobObjectType.Cluster:
        clusterLink = buildBaseLink(type, id);
        actionHostGroupLink = `${clusterLink}/configuration${pathToActionHostGroups}`;
        return { ...object, link: clusterLink };
      case AdcmJobObjectType.Service:
        serviceLink = `${clusterLink}${buildBaseLink(type, id)}`;
        actionHostGroupLink = `${serviceLink}${pathToActionHostGroups}`;
        return { ...object, link: serviceLink };
      case AdcmJobObjectType.Component:
        componentLink = `${serviceLink}${buildBaseLink(type, id)}`;
        actionHostGroupLink = `${componentLink}${pathToActionHostGroups}`;
        return { ...object, link: componentLink };
      default:
        return { ...object, link: buildBaseLink(type, id) };
    }
  });
};
