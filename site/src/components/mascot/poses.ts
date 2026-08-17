// 教学插画层共享元数据：小循姿态与拟物配角的一处定义。
// 边界与设计语言见 docs/adr/0009-teaching-illustration-layer-boundaries.md
// 与 docs/design/v3-illustration-design-spec.md（V3-2，2026-08-17）。

export type MascotPose = "calm" | "puzzled" | "insight" | "effort" | "done";

export interface MascotPoseMeta {
  value: MascotPose;
  label: string;
  description: string;
}

/** 小循 5 种基础姿态：只引导、不陈述产品事实（ADR-0009）。 */
export const mascotPoses: MascotPoseMeta[] = [
  { value: "calm", label: "平静", description: "默认向导状态：中性表情，双臂自然下垂，用于普通讲解与站旁陪伴。" },
  { value: "puzzled", label: "疑惑", description: "头顶问号、嘴部收圆，用于「操作前预测」与模糊指令演示，提示学员先猜再看。" },
  { value: "insight", label: "恍然", description: "头顶亮起灯泡、眯眼微笑，用于概念揭晓与对照解释，暖黄仅作状态提示色。" },
  { value: "effort", label: "努力", description: "挑眉抿嘴、举起双臂带运动短线与汗滴，用于学员动手实验与等待真实调用结果。" },
  { value: "done", label: "完成", description: "举旗并亮出胸口对勾徽章，用于可核验成果达成与单元完成提示。" },
];

export type CastRole = "key" | "package" | "track";

export interface CastRoleMeta {
  value: CastRole;
  label: string;
  description: string;
}

/** 拟物配角三件套：无生命、纯示意，不模拟任何服务商产品 UI（ADR-0009）。 */
export const castRoles: CastRoleMeta[] = [
  { value: "key", label: "带计费的钥匙", description: "W3 的 API key 拟物：证明身份的钥匙，每次开门掉一枚硬币进计费表，示意按用量扣费。" },
  { value: "package", label: "贴 token 标签的包裹", description: "请求/响应载体拟物：包裹上的标签承载真实记录的 token 数与耗时，由使用方传入。" },
  { value: "track", label: "环跑道", description: "W1 的 Agent loop 本体：输入→生成→调工具→观察决定 的闭环轨道与四个站点。" },
];

/** 插画层调色板（与站点 accent 同源）；对比度核算记录在 v3-illustration-design-spec.md。 */
export const illustrationPalette = [
  { token: "--xun-ink", light: "#1c2b26", dark: "#e9f5ef", usage: "描边与插画内文字" },
  { token: "--xun-accent", light: "#087f68", dark: "#6dd9bd", usage: "青绿主色（同源站点 accent）" },
  { token: "--xun-accent-deep", light: "#05604f", dark: "#9ff0d9", usage: "完成徽章等强调细节" },
  { token: "--xun-on-accent", light: "#ffffff", dark: "#17181c", usage: "accent 填充上的文字（站点数字、对勾）" },
  { token: "--xun-fill", light: "#eaf6f1", dark: "#143a32", usage: "身体/面板装饰填充（描边承托）" },
  { token: "--xun-paper", light: "#ffffff", dark: "#17181c", usage: "角色留白底" },
  { token: "--xun-yellow", light: "#ffd76a", dark: "#ffd76a", usage: "恍然灯泡、旗面等状态提示填充" },
  { token: "--xun-warn", light: "#b0492a", dark: "#e09a72", usage: "警示/计费状态提示（与 Claude Code mark 赤陶橙 #d97757 为不同色值）" },
] as const;
