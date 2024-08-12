import { AdcmConcerns, AdcmConcernServicePlaceholder, AdcmConcernType } from '@models/adcm/concern';
import { generatePath } from 'react-router-dom';

export interface ConcernObjectPathsData {
  path?: string;
  text: string;
}

const concernTypeUrlDict: Record<string, string> = {
  [AdcmConcernType.AdcmConfig]: '',
  [AdcmConcernType.ClusterConfig]: '/clusters/:clusterId/configuration/primary-configuration',
  [AdcmConcernType.ClusterImport]: '/clusters/:clusterId/import/',
  [AdcmConcernType.ServiceConfig]: '/clusters/:clusterId/services/:serviceId/primary-configuration/',
  [AdcmConcernType.ComponentConfig]:
    '/clusters/:clusterId/services/:serviceId/components/:componentId/primary-configuration/',
  [AdcmConcernType.HostConfig]: '/hosts/:hostId/primary-configuration/',
  [AdcmConcernType.ProviderConfig]: '/hostproviders/:providerId/primary-configuration/',
  [AdcmConcernType.HostComponent]: '/clusters/:clusterId/mapping/',
  [AdcmConcernType.ClusterServices]: '/clusters/:clusterId/services/', // the same route for the Requirement concern type
  [AdcmConcernType.Job]: '/jobs/:taskId/',
  [AdcmConcernType.Prototype]: '',
  [AdcmConcernType.Adcm]: '',
  [AdcmConcernType.Cluster]: '/clusters/:clusterId/',
  [AdcmConcernType.Service]: '/clusters/:clusterId/services/:serviceId/',
  [AdcmConcernType.Component]: '/clusters/:clusterId/services/:serviceId/components/:componentId/',
  [AdcmConcernType.Host]: '/hosts/:hostId/',
  [AdcmConcernType.Provider]: '/hostproviders/:providerId/',
};

export const getConcernLinkObjectPathsDataArray = (
  concerns: AdcmConcerns[] | undefined,
): Array<ConcernObjectPathsData[]> => {
  if (!concerns?.length) return [];
  const keyRegexp = /\${([^}]+)}/;

  return concerns.map((concern) => {
    if (!concern.reason || !concern.reason.placeholder) return [];
    const linksDataMap = new Map<string, ConcernObjectPathsData>();

    const separatedMessage = concern.reason.message.split(keyRegexp);

    Object.entries(concern.reason.placeholder).forEach(([key, placeholderItem]) => {
      const generatedPath = generatePath(concernTypeUrlDict[placeholderItem.type], placeholderItem.params);
      const clusterServiceId = (placeholderItem as AdcmConcernServicePlaceholder).params.serviceId;
      const path =
        placeholderItem.type === AdcmConcernType.ClusterImport && clusterServiceId
          ? `${generatedPath}/services/?serviceId=${clusterServiceId}`
          : generatedPath;
      linksDataMap.set(key, {
        path,
        text: placeholderItem.name,
      });
    });
    const initialLinksData: ConcernObjectPathsData[] = [];

    return separatedMessage.reduce((concernLinksData, text) => {
      if (text === '') return concernLinksData;
      if (linksDataMap.has(text)) {
        const linkData = linksDataMap.get(text);
        return [...concernLinksData, { path: linkData?.path || '', text: linkData?.text || '' }];
      }

      return [...concernLinksData, { text }];
    }, initialLinksData);
  });
};

export const isBlockingConcernPresent = (concerns: AdcmConcerns[]) => {
  return concerns.some(({ isBlocking }) => isBlocking);
};
