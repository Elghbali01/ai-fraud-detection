import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "overview" | "predict" | "upload" | "transactions" | "risk" | "explain"
  | "anomaly" | "investigations" | "system" | "menu" | "close" | "refresh"
  | "arrow" | "external" | "search" | "clock" | "check" | "alert" | "plus"
  | "file" | "chart" | "filter" | "shield" | "spark" | "chevron";

export function Icon({ name, ...props }: SVGProps<SVGSVGElement> & { name: IconName }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const shapes: Record<IconName, ReactNode> = {
    overview: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="3.5" width="7" height="4" rx="1.5" /><rect x="13.5" y="10.5" width="7" height="10" rx="1.5" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.5" /></>,
    predict: <path d="m13 2.8-8 10.3h6.1l-.6 8.1 8.5-11h-6.3l.3-7.4Z" />,
    upload: <><path d="M12 15.5V4.5" /><path d="m7.5 9 4.5-4.5L16.5 9" /><path d="M4 15v4a1.5 1.5 0 0 0 1.5 1.5h13A1.5 1.5 0 0 0 20 19v-4" /></>,
    transactions: <><rect x="4" y="4" width="16" height="16" rx="2.3" /><path d="M8 8h8M8 12h8M8 16h4" /></>,
    risk: <><path d="M12 3.2 20 6v5.8c0 4.8-3.5 7.8-8 9.5-4.5-1.7-8-4.7-8-9.5V6l8-2.8Z" /><path d="m8.8 12 2.1 2.1 4.5-4.6" /></>,
    explain: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /><path d="m19 15 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15Z" /></>,
    anomaly: <><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="3" /><path d="M12 1.8v2.1M12 20.1v2.1M1.8 12h2.1M20.1 12h2.1" /></>,
    investigations: <><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4V2.8h6V4M8.5 10h7M8.5 14h7M8.5 18h4" /></>,
    system: <><path d="M3 12h3l2-6 4 12 2.5-7 1.5 3H21" /></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
    refresh: <><path d="M20 7v5h-5" /><path d="M19.2 12a7.2 7.2 0 1 1-2.1-5.1L20 9" /></>,
    arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
    external: <><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4.2 4.2" /></>,
    clock: <><circle cx="12" cy="12" r="8.8" /><path d="M12 7v5.2l3.5 2" /></>,
    check: <path d="m5 12 4.2 4.2L19 6.5" />,
    alert: <><path d="M10.2 4.1 2.8 17a2 2 0 0 0 1.7 3h14.9a2 2 0 0 0 1.7-3L13.7 4.1a2 2 0 0 0-3.5 0Z" /><path d="M12 9v4.2M12 17h.01" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    file: <><path d="M7 3.5h7l4 4V20a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 20V5a1.5 1.5 0 0 1 1-1.5Z" /><path d="M14 3.8V8h4M9 13h6M9 17h6" /></>,
    chart: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2" /></>,
    filter: <><path d="M4 5h16l-6.2 7.2v5.3l-3.6 1.8v-7.1L4 5Z" /></>,
    shield: <><path d="M12 3 19 6v5.4c0 4.5-3.1 7.2-7 9-3.9-1.8-7-4.5-7-9V6l7-3Z" /><path d="M12 8v4M12 15h.01" /></>,
    spark: <><path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z" /><path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15Z" /></>,
    chevron: <path d="m8 10 4 4 4-4" />,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true" {...common} {...props}>{shapes[name]}</svg>;
}
