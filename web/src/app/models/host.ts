import { BaseEntity } from '@app/core/types';

export interface IHost extends BaseEntity {
  cluster_id?: number;
  cluster_url?: string;
  cluster_name?: string;
  clusters: any[];
  fqdn: string;
  host_id: number;
  host_url: string;
  monitoring: string;
  provider_id: number;
  provider_name: number;
  upgradable: boolean;
}
