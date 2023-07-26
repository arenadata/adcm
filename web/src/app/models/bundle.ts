import { AdcmEntity } from './entity';

export interface IBundle extends AdcmEntity {
  adcm_min_version: string;
  date: string;
  description: string;
  edition: string;
  hash: string;
  license: string;
  license_hash: any;
  license_path: any;
  license_url: string;
  name: string;
  update: string;
  url: string;
  version: string;
  signature_status: string;

}
