export const TERMINATE_RISK_WARNING =
  'This feature is intended for experienced users who are familiar with the potential risks and implications associated with the managed environments.';

export const getStopJobDialogTitle = (name: string) => `Stop the job "${name}"`;

export const getStopSubJobDialogTitle = (name: string) => `Stop subjob "${name}"`;

export const getSkipSubJobDialogTitle = (name: string) => `Skip subjob "${name}"`;

export const getStopSubJobDialogDescription = (name: string) =>
  `Subjob "${name}" will be stopped and the next subjob will be executed`;

export const getSkipSubJobDialogDescription = (name: string) =>
  `Subjob "${name}" will be skipped and the next subjob will be executed`;

export const getStopGroupDialogTitle = (name: string) => `Stop the group "${name}"`;

export const getSkipGroupDialogTitle = (name: string) => `Skip the group "${name}"`;

export const getStopGroupDialogDescription = (name: string) =>
  `Group "${name}" will be stopped and the next subjob will be executed`;

export const getSkipGroupDialogDescription = (name: string) =>
  `Group "${name}" will be skipped and the next subjob will be executed`;
