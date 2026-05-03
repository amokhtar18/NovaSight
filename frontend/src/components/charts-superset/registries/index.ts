export { Registry, RegistryWithLoader } from './Registry';
export type { Loader } from './Registry';

export { default as getChartMetadataRegistry } from './ChartMetadataRegistrySingleton';
export { default as getChartComponentRegistry } from './ChartComponentRegistrySingleton';
export type { ChartComponent } from './ChartComponentRegistrySingleton';
export { default as getChartControlPanelRegistry } from './ChartControlPanelRegistrySingleton';
export { default as getChartTransformPropsRegistry } from './ChartTransformPropsRegistrySingleton';
export { default as getChartBuildQueryRegistry } from './ChartBuildQueryRegistrySingleton';
