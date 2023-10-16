export interface UpgradeHostProviderFormData {
  upgradeId: number | null;
  isClusterUpgradeAcceptedLicense: boolean;
}

export interface UpgradeStepFormProps {
  formData: UpgradeHostProviderFormData;
  onChange: (changes: Partial<UpgradeHostProviderFormData>) => void;
}
