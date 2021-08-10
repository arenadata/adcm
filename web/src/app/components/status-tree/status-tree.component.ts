/* tslint:disable:member-ordering */
import { Component, Input } from '@angular/core';
import { FlatTreeControl } from '@angular/cdk/tree';
import { MatTreeFlatDataSource, MatTreeFlattener } from '@angular/material/tree';

import { StatusTree, StatusTreeSubject, SubjectStatus } from '@app/models/status-tree';

interface ExampleFlatNode {
  expandable: boolean;
  subject: StatusTreeSubject;
  level: number;
}

interface Counts {
  total: number;
  succeed: number;
}

interface CountedStatusTree extends StatusTree {
  counts?: Counts;
}

export enum Folding {
  Collapsed,
  Expanded,
}

@Component({
  selector: 'app-status-tree',
  templateUrl: './status-tree.component.html',
  styleUrls: ['./status-tree.component.scss']
})
export class StatusTreeComponent {

  SubjectStatus = SubjectStatus;

  private calcCounts = (children: CountedStatusTree[]): Counts => {
    return children.reduce((acc: Counts, child: CountedStatusTree) => {
        acc.total++;
        if (child.subject.status === SubjectStatus.Success) {
          acc.succeed++;
        }
        return acc;
      },
      { total: 0, succeed: 0 } as Counts,
    ) as Counts;
  }

  private transformer = (node: StatusTree, level: number) => {
    return {
      expandable: !!node.children && node.children.length > 0,
      subject: node.subject,
      level: level,
      counts: node.children ? this.calcCounts(node.children) : { total: 0, succeed: 0 },
    };
  }

  treeControl = new FlatTreeControl<ExampleFlatNode>(
  node => node.level,
  node => node.expandable,
  );

  treeFlattener = new MatTreeFlattener(
    this.transformer, node => node.level, node => node.expandable, node => node.children);

  dataSource = new MatTreeFlatDataSource(this.treeControl, this.treeFlattener);

  private ownTree: StatusTree[];
  @Input() set tree(tree: StatusTree[]) {
    this.ownTree = tree;
    this.dataSource.data = tree;

    if (this.folding === Folding.Expanded) {
      this.treeControl.expandAll();
    }

    if (this.folding === Folding.Collapsed) {
      this.treeControl.collapseAll();
    }
  }
  get tree(): StatusTree[] {
    return this.ownTree;
  }

  hasChild = (_: number, node: ExampleFlatNode) => node.expandable;

  private ownFolding: Folding;
  @Input() set folding(folding: Folding) {
    this.ownFolding = folding;
    this.tree = this.tree;
  }
  get folding(): Folding {
    return this.ownFolding;
  }

}
