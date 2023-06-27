export type BreadcrumbsItemConfig = {
  label: string;
  href?: string;
};

interface PageRouteConfig {
  pageTitle: string;
  breadcrumbs: BreadcrumbsItemConfig[];
}

export type RoutesConfigs = Record<string, PageRouteConfig>;

export type DynamicParameters = { [key: string]: string | undefined };

export type Route = {
  path: string;
  params: DynamicParameters;
};
