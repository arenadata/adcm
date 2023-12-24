export enum UpgradeStepKey {
  SelectUpgrade = 'select_upgrade',
  ServicesLicenses = 'service_license',
  UpgradeRunConfig = 'upgrade_run_config',
}

export interface UpgradeClusterFormData {
  upgradeId: number | null;
  isClusterUpgradeAcceptedLicense: boolean;
  servicesPrototypesAcceptedLicense: Set<number>;
}

export interface UpgradeStepFormProps {
  formData: UpgradeClusterFormData;
  onChange: (changes: Partial<UpgradeClusterFormData>) => void;
}
