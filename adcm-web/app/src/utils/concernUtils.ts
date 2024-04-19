import {
  AdcmConcernType,
  AdcmConcerns,
  AdcmConcernPlaceholder,
  AdcmConcernCause,
  AdcmConcernClusterPlaceholder,
} from '@models/adcm/concern';

export interface ConcernObjectPathsData {
  path?: string;
  text: string;
}

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
      const path = getConcernPath(concern, placeholderItem);
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

export const getConcernObjectPath = (placeholderProps: AdcmConcernPlaceholder): string => {
  switch (placeholderProps.type) {
    case AdcmConcernType.Cluster:
      return `/clusters/${placeholderProps.params.clusterId}`;
    case AdcmConcernType.Service:
      return `/clusters/${placeholderProps.params.clusterId}/services/${placeholderProps.params.serviceId}`;
    case AdcmConcernType.Component:
      return `/clusters/${placeholderProps.params.clusterId}/services/${placeholderProps.params.serviceId}/components/${placeholderProps.params.componentId}`;
    case AdcmConcernType.Host:
      return `/hosts/${placeholderProps.params.hostId}`;
    case AdcmConcernType.Provider:
      return `/hostproviders/${placeholderProps.params.providerId}`;
    case AdcmConcernType.Job:
      return `/jobs/${placeholderProps.params.jobId}`;
    case AdcmConcernType.Prototype:
    case AdcmConcernType.Adcm:
    default:
      return '';
  }
};

const getConcernObjectConfigPath = (placeholderProps: AdcmConcernPlaceholder, concernCause?: AdcmConcernCause) => {
  const clusterPath = `/clusters/${(placeholderProps as AdcmConcernClusterPlaceholder).params.clusterId}`;
  const concernObjectPath = getConcernObjectPath(placeholderProps);

  if (placeholderProps.type === AdcmConcernType.Cluster && concernCause === AdcmConcernCause.Config) {
    return `${clusterPath}/configuration`;
  } else {
    return `${concernObjectPath}/primary-configuration`;
  }
};

const getConcernPath = (concern: AdcmConcerns, placeholderProps: AdcmConcernPlaceholder): string => {
  if (placeholderProps.type === AdcmConcernType.Prototype || placeholderProps.type === AdcmConcernType.Adcm) {
    return '';
  }

  const clusterPath = `/clusters/${(placeholderProps as AdcmConcernClusterPlaceholder).params.clusterId}`;

  const concernObjectPath = getConcernObjectPath(placeholderProps);

  switch (concern.cause) {
    case AdcmConcernCause.Config:
      return getConcernObjectConfigPath(placeholderProps, AdcmConcernCause.Config);
    case AdcmConcernCause.HostComponent:
      return `${clusterPath}/mapping`;
    case AdcmConcernCause.Import:
      return `${clusterPath}/import/${
        placeholderProps.type === AdcmConcernType.Service
          ? `services/?serviceId=${placeholderProps.params.serviceId}`
          : placeholderProps.type
      }`;
    case AdcmConcernCause.Service:
    case AdcmConcernCause.Requirement:
      return `${clusterPath}/services`;
    case AdcmConcernCause.Job:
      return concernObjectPath;
    default:
      return placeholderProps.type === AdcmConcernType.Cluster
        ? clusterPath
        : getConcernObjectConfigPath(placeholderProps);
  }
};

export const isBlockingConcernPresent = (concerns: AdcmConcerns[]) => {
  return concerns.some(({ isBlocking }) => isBlocking);
};
