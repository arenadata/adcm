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
import { Component } from '@angular/core';

@Component({
  selector: 'app-intro',
  template: `
    <p>
      This is <a [href]="adcm_docs" target="_blank">Arenadata Cluster Manager (ADCM)</a> - the home of all your data. It connects together different data applications, providing a fast, reliable and enterprise-ready way to
      manage your data landscape. Please read this short notice to start using ADCM in its most efficient way.
    </p>
    <div class="admin-warn">
      <ul>
        <li>
          <i
            >We have to know ADCM's Url [ <b style="color: #00e676;">{{ adcm_url }}</b> ] to send information from host. We try to guess that information from url you enter in
            browser. <br />But if your network has more complicated structure and we guess wrong, <a routerLink="/admin/settings">please fix that here</a>.</i
          >
        </li>
      </ul>
    </div>
    <h3>Bundle</h3>
    <p>
      Bundle is a set of functionality that you can add to your ADCM. Every data application (Database, Hadoop cluster, etc.) is created using a bundle. For example, to start a
      Hadoop cluster version 3.0.0, you will need a Hadoop 3.0.0 bundle. Other bundles may contain virtual machine access method (Amazon, Google, etc.), widgets, etc. Think of it
      like a plugin, or a mobile phone application.
    </p>
    <h3>Cluster</h3>
    <p>
      This is the main functionality. Cluster is a set of hosts, running one distributed application. Cluster is deployed from bundle. Of course, you can have multiple clusters set
      up from the same bundle.
    </p>
    <h3>Service</h3>
    <p>
      Service is a part of a cluster. It contain part of the cluster functionality. Service can run across all hosts in the cluster, or only across some of them.
    </p>
    <h3>Component</h3>
    <p>
      Component is a part of a service that is running on one host.
    </p>
    <h3>Hostprovider</h3>
    <p>
      Hostprovider is a set of access credentials for ADCM to create new hosts or access existing, For example, when you want to create a VM in a public cloud, you will need to add
      username, access key and other access credentials to ADCM. Do it by creating a new Hostprovider and editing its config.
    </p>
    <h3>Host</h3>
    <p>
      This is a machine that your data app is running on. A host may be a virtual machine, a physical server, or something else.<br />
      A host can be added to only one cluster - you cannot share a host between multiple clusters.
    </p>
    <p>&nbsp;</p>
    Shortly:
    <ul>
      <li>Bundle is a packet with functionality (ex. Hadoop)</li>
      <li>Cluster is a logical set of functionality. Cluster is created from bundle (ex Hadoop cluster)</li>
      <li>Service is a logical part of cluster (ex. HDFS)</li>
      <li>Component is a part of service, that is located on some host (ex. DataNode)</li>
    </ul>
    If you need a more deep dive into ADCM's functionality,
    <a [href]="adcm_docs" target="_blank">start from docs</a>.
    <br />
    Now you are ready to start exploring ADCM by yourself - enjoy it!
    <p>&nbsp;</p>
  `,
  styles: [':host {padding: 0 10px;}', '.admin-warn {border:solid 1px #ff9800;margin-right: 20px;}', '.admin-warn ul li {padding: 8px 0;}'],
})
export class IntroComponent {
  adcm_url = `${location.protocol}//${location.host}`;

  adcm_docs = 'https://docs.arenadata.io/en/ADCM/current/introduction/intro.html';
}
