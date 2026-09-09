import { type AdcmSubJobLogCheckContentItem, AdcmSubJobLogSeverity, AdcmJobStatus } from '@models/adcm';
import type { SubJobLogNode } from './SubJobLogCheck.types';
import { getStatusLabel } from '@utils/humanizationUtils.ts';

const SEVERITY_TO_STATUS: Record<AdcmSubJobLogSeverity, AdcmJobStatus> = {
  [AdcmSubJobLogSeverity.Error]: AdcmJobStatus.Failed,
  [AdcmSubJobLogSeverity.Warning]: AdcmJobStatus.Warning,
  [AdcmSubJobLogSeverity.Info]: AdcmJobStatus.Info,
};

const SEVERITY_PRIORITY: AdcmSubJobLogSeverity[] = [
  AdcmSubJobLogSeverity.Error,
  AdcmSubJobLogSeverity.Warning,
  AdcmSubJobLogSeverity.Info,
];

export const isConcreteSeverityPresent = (
  content: AdcmSubJobLogCheckContentItem[],
  severityToCheck: AdcmSubJobLogSeverity,
) => content.some(({ result, severity }) => !result && severity === severityToCheck);

const getChildlessNodeSeverityBasedStatus = ({ severity, result }: AdcmSubJobLogCheckContentItem) => {
  if (result && severity) {
    return AdcmJobStatus.Success;
  }

  if (!result && severity && severity in SEVERITY_TO_STATUS) {
    return SEVERITY_TO_STATUS[severity];
  }

  return AdcmJobStatus.Failed;
};

const getNodeWithChildrenSeverityBasedStatus = (logContent: AdcmSubJobLogCheckContentItem[]): AdcmJobStatus => {
  const foundSeverity = SEVERITY_PRIORITY.find((severity) => isConcreteSeverityPresent(logContent, severity));

  return foundSeverity ? SEVERITY_TO_STATUS[foundSeverity] : AdcmJobStatus.Success;
};

const getSeverityBasedStatus = (data: AdcmSubJobLogCheckContentItem) => {
  if (data.content) {
    return getNodeWithChildrenSeverityBasedStatus(data.content);
  }

  return getChildlessNodeSeverityBasedStatus(data);
};

export const getRootNodeStatus = (logContent: AdcmSubJobLogCheckContentItem[], subJobStatus: string) => {
  if (subJobStatus === AdcmJobStatus.Running) {
    return AdcmJobStatus.Running;
  }

  return getNodeWithChildrenSeverityBasedStatus(logContent);
};

export const checkItemToNode = ({ content, ...data }: AdcmSubJobLogCheckContentItem, key: number): SubJobLogNode => {
  return {
    data: {
      ...data,
      status: getSeverityBasedStatus(data),
    },
    key: `${key}`,
    index: key,
    children: content?.map((item, index) => checkItemToNode(item, index)),
  };
};

export const getSubJobStatusLabel = (status: AdcmJobStatus) => {
  const subJobStatusLabelDict: Partial<Record<AdcmJobStatus, string>> = {
    [AdcmJobStatus.Failed]: 'Error',
    [AdcmJobStatus.Running]: 'Processing',
  };

  return subJobStatusLabelDict[status] ?? getStatusLabel(status);
};

export const calculateAndSetChildrenBorderHeight = (node: Element | null, parentY = 0) => {
  if (!node) return;

  const trigger = node.querySelector<HTMLDivElement>('.collapseNode__trigger');

  if (!trigger) return;

  const { top, height } = trigger.getBoundingClientRect();
  const triggerBottomY = top + height;
  const triggerCenterY = top + height / 2;

  const verticalBorderHeight = triggerCenterY - parentY;
  trigger.style.setProperty('--verticalBorderHeight', `${verticalBorderHeight}px`);

  const children = node.querySelector('.collapseNode__children')?.children[0].children;

  if (children) {
    Array.from(children).forEach((child) => calculateAndSetChildrenBorderHeight(child, triggerBottomY));
  }
};
