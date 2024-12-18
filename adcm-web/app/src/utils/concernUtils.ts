import type { AdcmConcerns, AdcmConcernServicePlaceholder } from '@models/adcm/concern';
import { AdcmConcernPlaceholderType } from '@models/adcm/concern';
import { generatePath } from 'react-router-dom';

export interface ConcernObjectPathsData {
  path?: string;
  text: string;
}

const concernPlaceholderTypeUrlDict: Record<string, string> = {
  [AdcmConcernPlaceholderType.AdcmConfig]: '',
  [AdcmConcernPlaceholderType.ClusterConfig]: '/clusters/:clusterId/configuration/primary-configuration',
  [AdcmConcernPlaceholderType.ClusterImport]: '/clusters/:clusterId/import/',
  [AdcmConcernPlaceholderType.ServiceConfig]: '/clusters/:clusterId/services/:serviceId/primary-configuration/',
  [AdcmConcernPlaceholderType.ComponentConfig]:
    '/clusters/:clusterId/services/:serviceId/components/:componentId/primary-configuration/',
  [AdcmConcernPlaceholderType.HostConfig]: '/hosts/:hostId/primary-configuration/',
  [AdcmConcernPlaceholderType.ProviderConfig]: '/hostproviders/:providerId/primary-configuration/',
  [AdcmConcernPlaceholderType.HostComponent]: '/clusters/:clusterId/mapping/',
  [AdcmConcernPlaceholderType.ClusterServices]: '/clusters/:clusterId/services/', // the same route for the Requirement concern type
  [AdcmConcernPlaceholderType.Job]: '/jobs/:taskId/', // backend sends taskId as jobId
  [AdcmConcernPlaceholderType.Prototype]: '',
  [AdcmConcernPlaceholderType.Adcm]: '',
  [AdcmConcernPlaceholderType.Cluster]: '/clusters/:clusterId/',
  [AdcmConcernPlaceholderType.Service]: '/clusters/:clusterId/services/:serviceId/',
  [AdcmConcernPlaceholderType.Component]: '/clusters/:clusterId/services/:serviceId/components/:componentId/',
  [AdcmConcernPlaceholderType.Host]: '/hosts/:hostId/',
  [AdcmConcernPlaceholderType.Provider]: '/hostproviders/:providerId/',
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
      const generatedPath = generatePath(concernPlaceholderTypeUrlDict[placeholderItem.type], placeholderItem.params);
      const clusterServiceId = (placeholderItem as AdcmConcernServicePlaceholder).params.serviceId;
      const path =
        placeholderItem.type === AdcmConcernPlaceholderType.ClusterImport && clusterServiceId
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
        // biome-ignore lint/performance/noAccumulatingSpread: TODO: refactor the thing
        return [...concernLinksData, { path: linkData?.path || '', text: linkData?.text || '' }];
      }
      // biome-ignore lint/performance/noAccumulatingSpread: TODO: refactor the thing
      return [...concernLinksData, { text }];
    }, initialLinksData);
  });
};

export const isBlockingConcernPresent = (concerns: AdcmConcerns[]) => {
  return concerns.some(({ isBlocking }) => isBlocking);
};

export const isIssueConcernPresent = (concerns: AdcmConcerns[]) => {
  return concerns.some(({ type }) => type === 'issue');
};
