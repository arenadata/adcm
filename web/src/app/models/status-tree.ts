export interface StatusTreeSubject {
  id?: number;
  name: string;
  status?: number;
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
  hc: StatusTreeSubject[];
}

export interface ServiceStatusTree extends StatusTreeSubject {
  hc: HostComponentStatusTree[];
}
