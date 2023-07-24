export interface AdcmConcernReason {
  message: string;
  placeholder: {
    source: {
      id: number;
      name: string;
      type: string;
    };
    target: {
      id: number;
      name: string;
      type: string;
    };
  };
}

export interface AdcmConcerns {
  id: number;
  reason: AdcmConcernReason;
  isBlocking: boolean;
}
