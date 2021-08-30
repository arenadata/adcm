const loadConfigGroup = () => import('./config-group.module').then((m) => m.ConfigGroupModule);

export { loadConfigGroup };
