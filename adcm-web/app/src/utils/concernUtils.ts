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

interface ConcernObjectData {
  concernId: number;
  isDeletable: boolean;
  concernData: ConcernObjectPathsData[];
}

export const getConcernLinkObjectPathsDataArray = (concerns?: AdcmConcerns[]): Array<ConcernObjectData> => {
  if (!concerns?.length) return [];

  const keyRegexp = /\${([^}]+)}/;

  return concerns.map((concern) => {
    const concernId = concern.id;
    const isDeletable = !concern.isBlocking;

    // If there is no reason or placeholder, return an object with an empty concernData
    if (!concern.reason?.placeholder) {
      return { concernId, isDeletable, concernData: [] };
    }

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

    const concernData = separatedMessage.reduce((accPathsData: ConcernObjectPathsData[], text: string) => {
      if (text !== '') {
        const linkData = linksDataMap.get(text);
        if (linkData) {
          const { path = '', text: textValue = '' } = linkData;
          accPathsData.push({ path, text: textValue });
        } else {
          accPathsData.push({ text });
        }
      }
      return accPathsData;
    }, [] as ConcernObjectPathsData[]);

    return { concernId, isDeletable, concernData };
  });
};

export const isBlockingConcernPresent = (concerns: AdcmConcerns[]) => {
  return concerns.some(({ isBlocking }) => isBlocking);
};

export const isIssueConcernPresent = (concerns: AdcmConcerns[]) => {
  return concerns.some(({ type }) => type === 'issue');
};
