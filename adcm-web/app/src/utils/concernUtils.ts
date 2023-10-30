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

    Object.entries(concern.reason.placeholder).forEach(([key, placeHolderItem]) => {
      const path = getConcernPath(concern, placeHolderItem);
      linksDataMap.set(key, {
        path,
        text: placeHolderItem.name,
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

export const getConcernObjectPath = (placeHolderProps: AdcmConcernPlaceholder): string => {
  switch (placeHolderProps.type) {
    case AdcmConcernType.Cluster:
      return `/clusters/${placeHolderProps.params.clusterId}`;
    case AdcmConcernType.Service:
      return `/clusters/${placeHolderProps.params.clusterId}/services/${placeHolderProps.params.serviceId}`;
    case AdcmConcernType.Component:
      return `/clusters/${placeHolderProps.params.clusterId}/services/${placeHolderProps.params.serviceId}/components/${placeHolderProps.params.componentId}`;
    case AdcmConcernType.Host:
      return `/hosts/${placeHolderProps.params.hostId}`;
    case AdcmConcernType.Provider:
      return `/hostproviders/${placeHolderProps.params.providerId}`;
    case AdcmConcernType.Job:
      return `/jobs/${placeHolderProps.params.jobId}`;
    case AdcmConcernType.Prototype:
    default:
      return '';
  }
};

const getConcernPath = (concern: AdcmConcerns, placeHolderProps: AdcmConcernPlaceholder): string => {
  if (placeHolderProps.type === AdcmConcernType.Prototype) {
    return '';
  }

  const clusterPath = `/clusters/${(placeHolderProps as AdcmConcernClusterPlaceholder).params.clusterId}`;

  switch (concern.cause) {
    case AdcmConcernCause.Config:
      return `${getConcernObjectPath(placeHolderProps)}/primary-configuration`;
    case AdcmConcernCause.HostComponent:
      return `${clusterPath}/mapping`;
    case AdcmConcernCause.Import:
      return `${clusterPath}/import/${
        placeHolderProps.type === 'service'
          ? `services/?serviceId=${placeHolderProps.params.serviceId}`
          : placeHolderProps.type
      }`;
    case AdcmConcernCause.Service:
    case AdcmConcernCause.Requirement:
      return `${clusterPath}/services`;
    case AdcmConcernCause.Job:
      return `${getConcernObjectPath(placeHolderProps)}`;
    default:
      return '';
  }
};
