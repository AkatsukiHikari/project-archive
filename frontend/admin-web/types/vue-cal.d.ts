declare module "vue-cal" {
  import type { DefineComponent } from "vue";
  const VueCal: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>;
  export default VueCal;
}

declare module "vue-cal/dist/vuecal.css" {}
