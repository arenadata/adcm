// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { ClusterComponent } from './cluster.component';
import { DumbComponent } from './dumb.component';
import { EmbedComponent } from './embed.component';
import { HostComponent } from './host.component';
import { InsideComponent } from './inside/inside.component';
import { StackComponent } from './stack.component';

export const WidgetTypeGroups = [
  {
    name: 'Grafana',
    types: [
      { value: 'Grafana_Embed', title: 'Embed Panel' },
      { value: 'Grafana_Image', title: 'Direct Link Rendered Image' },
    ],
  },

  {
    name: 'System',
    types: [
      { value: 'intro', title: 'Intro' },
      { value: 'cluster', title: 'Clusters' },
      { value: 'host', title: 'Hosts' },
      { value: 'stack', title: 'Bundles' },
      { value: 'inside', title: 'Inside'}
    ],
  },

  {
    name: 'YouTube',
    disabled: true,
    types: [
      { value: 'charmander-6', title: 'Charmander' },
      { value: 'vulpix-7', title: 'Vulpix' },
      { value: 'flareon-8', title: 'Flareon' },
    ],
  },
];

export const PROTOTYPE_WIDGETS = {
  Grafana_Embed: {
    component: EmbedComponent,
    data: {
      type: 'iframe',
      src:
        'https://snapshot.raintank.io/dashboard-solo/snapshot/y7zwi2bZ7FcoTlB93WN7yWO4aMiz3pZb?from=1493369923321&to=1493377123321&panelId=4',
    },
  },
  Grafana_Image: {
    component: EmbedComponent,
    data: {
      type: 'image',
      src:
        'http://play.grafana.org/render/dashboard-solo/db/grafana-play-home?orgId=1&panelId=4&from=1499272191563&to=1499279391563&width=1000&height=500&tz=UTC%2B02%3A00&timeout=5000',
    },
  },

  stack: { component: StackComponent },
  cluster: { component: ClusterComponent },
  host: { component: HostComponent },
  inside: { component: InsideComponent },
  intro: {
    component: DumbComponent,
    data: {
      html: `<p>This is Arenadata Cluster Manager (ADCM) - the home of all your data. 
      It connects together different data applications, providing a fast, reliable and enterprise-ready way to manage your data landscape.
      Please read this short notice to start use ADCM in its most efficient way.
      </p>
      <h3>Bundle</h3>
      <p>
      Bundle is a set of functionality that you can add to your ADCM. 
      Every data application (Database, Hadoop cluster, etc.) is created using a bundle. 
      For example, to start a Hadoop cluster version 3.0.0, you will need a Hadoop 3.0.0 bundle.
      Other bundles may contain virtual machine access method (Amazon, Google, etc.), widgets, etc.
      Think of it like a plugin, or a mobile phone application.
      </p>
      <h3>Cluster</h3>
      <p>
      This is the main functionality. Cluster is a set of hosts, running one distributed application. 
      Cluster is deployed from bundle. Of course, you can have multiple clusters set up from the same bundle.
      </p>
      <h3>Service</h3>
      <p>
      Service is a part of a cluster. It contain part of the cluster functionality. 
      Service can run across all hosts in the cluster, or only across some of them.
      </p>

      <h3>Component</h3>
      <p>
      Component is a part of a service that is running on one host.
      </p>
      <h3>Hostprovider</h3>
      <p>
      Hostprovider is a set of access credentials for ADCM to create new hosts or access existing, 
      For example, when you want to create a VM in a public cloud, you will need to add username, access key and other access credentials to ADCM. 
      Do it by creating a new Hostprovider and editing its config.
      </p>
      <h3>Host</h3>
      <p>
      This is a machine that your data app is running on. A host may be a virtual machine, a physical server, or something else.<br/>
      A host can be added to only one cluster - you cannot share a host between multiple clusters.
      </p>
      <p>&nbsp;</p>      
      <p>
      Shortly:
      <ul>
      <li>Bundle is a packet with functionality (ex. Hadoop)</li>
      <li>Cluster is a logical set of functionality. Cluster is created from bundle (ex Hadoop cluster)</li>
      <li>Service is a logical part of cluster (ex. HDFS)</li>
      <li>Component is a part of service, that is located on some host (ex. DataNode)</li>
      </ul>
      If you need a more deep dive into ADCM's functionality, <a href="https://docs.arenadata.io/adcm/" target="_blank">start from docs</a>.<br/>
      Now you are ready to start exploring ADCM by yourself - enjoy it!
      </p>`,
    },
  },
};
