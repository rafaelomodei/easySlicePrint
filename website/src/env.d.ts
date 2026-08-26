/// <reference path="../.astro/types.d.ts" />

declare module "*.toml?raw" {
  const content: string;
  export default content;
}
