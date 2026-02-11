/**
 * 图可视化配置
 * 用于管理图可视化的各种限制和参数
 */

export interface GraphConfig {
  /** 最大节点数量限制 */
  maxNodes: number;
  /** 最大边数量限制 */
  maxEdges: number;
  /** 节点数量阈值，超过此数量时隐藏标签 */
  hideLabelsThreshold: number;
  /** 力模拟参数 */
  forceSimulation: {
    /** 默认节点距离 */
    defaultDistance: number;
    /** 大图节点距离 */
    largeGraphDistance: number;
    /** 默认电荷强度 */
    defaultChargeStrength: number;
    /** 大图电荷强度 */
    largeGraphChargeStrength: number;
    /** 默认碰撞半径 */
    defaultCollisionRadius: number;
    /** 大图碰撞半径 */
    largeGraphCollisionRadius: number;
    /** Alpha衰减率 */
    alphaDecay: number;
    /** 速度衰减率 */
    velocityDecay: number;
  };
}

/**
 * 默认图配置
 */
export const defaultGraphConfig: GraphConfig = {
  maxNodes: 500,
  maxEdges: 1000,
  hideLabelsThreshold: 200,
  forceSimulation: {
    defaultDistance: 100,
    largeGraphDistance: 80,
    defaultChargeStrength: -300,
    largeGraphChargeStrength: -200,
    defaultCollisionRadius: 40,
    largeGraphCollisionRadius: 30,
    alphaDecay: 0.022,
    velocityDecay: 0.4,
  },
};

/**
 * 获取图配置
 * 可以从环境变量或配置文件读取，目前返回默认配置
 */
export function getGraphConfig(): GraphConfig {
  // 从环境变量读取配置（Vite 使用 import.meta.env）
  // 环境变量需要以 VITE_ 开头才能在客户端访问
  const maxNodes = parseInt(
    (import.meta.env.VITE_MAX_GRAPH_NODES as string) || 
    (import.meta.env.REACT_APP_MAX_GRAPH_NODES as string) || 
    '500', 
    10
  );
  const maxEdges = parseInt(
    (import.meta.env.VITE_MAX_GRAPH_EDGES as string) || 
    (import.meta.env.REACT_APP_MAX_GRAPH_EDGES as string) || 
    '1000', 
    10
  );
  const hideLabelsThreshold = parseInt(
    (import.meta.env.VITE_HIDE_LABELS_THRESHOLD as string) || 
    (import.meta.env.REACT_APP_HIDE_LABELS_THRESHOLD as string) || 
    '200', 
    10
  );

  return {
    ...defaultGraphConfig,
    maxNodes,
    maxEdges,
    hideLabelsThreshold,
  };
}

/**
 * 图配置实例（单例）
 */
export const graphConfig = getGraphConfig();

