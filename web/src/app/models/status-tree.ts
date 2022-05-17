export type StatusTreeLinkFunc = (id: number, tree: StatusTree[]) => string[];

export interface StatusTreeSubject {
  id?: number;
  name: string;
  status?: number;
  link?: StatusTreeLinkFunc;
}

export interface HCStatusTreeSubject extends StatusTreeSubject {
  service_id: number;
}

export interface StatusTree {
  subject: StatusTreeSubject;
  children: StatusTree[];
}

export interface ClusterStatusTree extends StatusTreeSubject {
  chilren: {
    hosts: StatusTreeSubject[];
    services: ServiceStatusTree[];
  };
}

export interface ServiceStatusTree extends StatusTreeSubject {
  hc: HostComponentStatusTree[];
}

export interface HostComponentStatusTree extends StatusTreeSubject {
  hosts: StatusTreeSubject[];
}

export interface HostStatusTree extends StatusTreeSubject {
  hc: HCStatusTreeSubject[];
}

export interface ServiceStatusTree extends StatusTreeSubject {
  hc: HostComponentStatusTree[];
}
