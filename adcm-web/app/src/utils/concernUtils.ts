import { AdcmConcernType, AdcmConcerns, AdcmConcernPlaceholder, AdcmConcernCause } from '@models/adcm/concern';

export interface ConcernLinksData {
  linkPath?: string;
  text: string;
}

export const getConcernLinksDataArray = (concerns: AdcmConcerns[] | undefined): Array<ConcernLinksData[]> => {
  if (!concerns?.length) return [];
  const keyRegexp = /\${([^}]+)}/;

  return concerns.map((concern) => {
    if (!concern.reason || !concern.reason.placeholder) return [];
    const linksDataMap = new Map<string, ConcernLinksData>();

    const separatedMessage = concern.reason.message.split(keyRegexp);

    Object.entries(concern.reason.placeholder).forEach(([key, placeHolderItem]) => {
      const linkPath = getConcernLink(placeHolderItem) + getConcernTab(concern);
      linksDataMap.set(key, {
        linkPath,
        text: placeHolderItem.name,
      });
    });
    const initialLinksData: ConcernLinksData[] = [];

    return separatedMessage.reduce((concernLinksData, text) => {
      if (text === '') return concernLinksData;
      if (linksDataMap.has(text)) {
        const linkData = linksDataMap.get(text);
        return [...concernLinksData, { linkPath: linkData?.linkPath || '', text: linkData?.text || '' }];
      }

      return [...concernLinksData, { text }];
    }, initialLinksData);
  });
};

export const getConcernTab = (concern: AdcmConcerns): string => {
  switch (concern.cause) {
    case AdcmConcernCause.Config:
      return '/primary-configuration';
    case AdcmConcernCause.HostComponent:
      return '/mapping';
    case AdcmConcernCause.Import:
      return '/import';
    case AdcmConcernCause.Service:
    case AdcmConcernCause.Requirement:
      return '/services';
    default:
      return '';
  }
};

export const getConcernLink = (placeHolderProps: AdcmConcernPlaceholder): string => {
  if (placeHolderProps.type === AdcmConcernType.Cluster) {
    return `/clusters/${placeHolderProps.params.clusterId}`;
  }

  if (placeHolderProps.type === AdcmConcernType.Service) {
    return `/clusters/${placeHolderProps.params.clusterId}/services/${placeHolderProps.params.serviceId}`;
  }

  if (placeHolderProps.type === AdcmConcernType.Component) {
    return `/clusters/${placeHolderProps.params.clusterId}/services/${placeHolderProps.params.serviceId}/components/${placeHolderProps.params.componentId}`;
  }

  if (placeHolderProps.type === AdcmConcernType.Host) {
    return `/hosts/${placeHolderProps.params.hostId}`;
  }

  if (placeHolderProps.type === AdcmConcernType.Provider) {
    return `/hostprovider/${placeHolderProps.params.providerId}`;
  }

  if (placeHolderProps.type === AdcmConcernType.Job) {
    return `/jobs/${placeHolderProps.params.jobId}/`;
  }

  return '';
};
