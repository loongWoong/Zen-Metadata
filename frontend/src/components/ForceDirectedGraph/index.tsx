import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import type { GraphData, GraphNode, GraphEdge } from '../../types';
import { graphConfig } from '../../utils/graphConfig';

interface ForceDirectedGraphProps {
  data: GraphData;
  width?: number;
  height?: number;
  maxNodes?: number;
  maxEdges?: number;
  showNodeLabels?: boolean;
  showEdgeLabels?: boolean;
  onNodeClick?: (node: GraphNode) => void;
  onNodeHover?: (node: GraphNode | null) => void;
}

interface D3Node extends GraphNode {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

interface D3Edge extends GraphEdge {
  source: string | D3Node;
  target: string | D3Node;
}

// 节点类型颜色映射
const nodeTypeColors: Record<string, string> = {
  // 元模型图专用颜色（与图例一致）
  entity: '#1890ff',      // 实体元模型 - 蓝色
  collector: '#fa8c16',   // 采集器 - 橙色
  // 其他类型颜色（保持向后兼容）
  file: '#1890ff',
  directory: '#52c41a',
  function: '#fa8c16',
  class: '#eb2f96',
  table: '#722ed1',
  column: '#13c2c2',
  database: '#2f54eb',
  schema: '#faad14',
  package: '#f5222d',
  module: '#a0d911',
  default: '#8c8c8c',
};

// 使用配置中的限制值

export default function ForceDirectedGraph({
  data,
  width = 1000,
  height = 600,
  maxNodes,
  maxEdges,
  showNodeLabels = false,
  showEdgeLabels = false,
  onNodeClick,
  onNodeHover,
}: ForceDirectedGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simulationRef = useRef<d3.Simulation<D3Node, D3Edge> | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width, height });
  
  // 性能优化：节流tick更新
  const rafRef = useRef<number | null>(null);
  const lastUpdateRef = useRef<number>(0);

  // 自适应大小
  const updateDimensions = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setDimensions({
        width: rect.width || width,
        height: rect.height || height,
      });
    }
  }, [width, height]);

  useEffect(() => {
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    
    // 使用 ResizeObserver 监听容器尺寸变化
    const resizeObserver = new ResizeObserver(() => {
      updateDimensions();
    });
    
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    
    return () => {
      window.removeEventListener('resize', updateDimensions);
      resizeObserver.disconnect();
    };
  }, [updateDimensions]);

  // 当数据变化时，延迟更新尺寸（确保DOM已更新）
  // 注意：移除updateDimensions依赖，避免无限循环
  useEffect(() => {
    if (!data.nodes.length) return;
    const timer = setTimeout(() => {
      updateDimensions();
    }, 100);
    return () => clearTimeout(timer);
  }, [data.nodes.length, data.edges.length]); // 只依赖数据长度，不依赖整个data对象

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    const currentWidth = dimensions.width;
    const currentHeight = dimensions.height;

    // 性能优化：限制节点和边数量（优先使用传入的配置值，否则使用默认配置）
    const nodeLimit = maxNodes ?? graphConfig.maxNodes;
    const edgeLimit = maxEdges ?? graphConfig.maxEdges;
    const limitedNodes = data.nodes.slice(0, nodeLimit);
    const limitedEdges = data.edges.slice(0, edgeLimit).filter(edge => {
      const sourceId = String(edge.source);
      const targetId = String(edge.target);
      return limitedNodes.some(n => String(n.id) === sourceId) && 
             limitedNodes.some(n => String(n.id) === targetId);
    });

    // 如果数据被截断，在控制台提示（仅开发环境）
    if (import.meta.env.DEV && (data.nodes.length > nodeLimit || data.edges.length > edgeLimit)) {
      console.warn(`图数据已截断: 节点 ${data.nodes.length} -> ${limitedNodes.length}, 边 ${data.edges.length} -> ${limitedEdges.length}`);
    }

    // 停止之前的模拟
    if (simulationRef.current) {
      simulationRef.current.stop();
    }

    // 清除之前的渲染
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current);
    const g = svg.append('g');

    // 创建缩放和平移行为
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // 初始化节点和边（使用限制后的数据）
    const nodes: D3Node[] = limitedNodes.map((node) => ({
      ...node,
      x: Math.random() * currentWidth,
      y: Math.random() * currentHeight,
    }));

    // 创建节点ID到节点的映射
    const nodeMap = new Map<string, D3Node>();
    nodes.forEach((node) => {
      nodeMap.set(String(node.id), node);
    });

    // 过滤并创建边，确保 source 和 target 都存在
    const links: Array<D3Edge & { sourceId: string; targetId: string }> = limitedEdges
      .filter((edge) => {
        const sourceId = String(edge.source);
        const targetId = String(edge.target);
        return nodeMap.has(sourceId) && nodeMap.has(targetId);
      })
      .map((edge) => {
        const sourceId = String(edge.source);
        const targetId = String(edge.target);
        return {
          ...edge,
          source: sourceId,
          target: targetId,
          sourceId,
          targetId,
        };
      });

    // 移除调试信息，避免控制台刷屏

    // 创建力模拟 - 性能优化：根据节点数量调整参数（使用配置值）
    const nodeCount = nodes.length;
    const threshold = graphConfig.hideLabelsThreshold;
    const config = graphConfig.forceSimulation;
    const distance = nodeCount > threshold ? config.largeGraphDistance : config.defaultDistance;
    const chargeStrength = nodeCount > threshold ? config.largeGraphChargeStrength : config.defaultChargeStrength;
    const collisionRadius = nodeCount > threshold ? config.largeGraphCollisionRadius : config.defaultCollisionRadius;
    
    const simulation = d3
      .forceSimulation<D3Node>(nodes)
      .force(
        'link',
        d3
          .forceLink<D3Node, D3Edge>(links)
          .id((d) => String(d.id))
          .distance(distance)
          .strength(0.5)
      )
      .force('charge', d3.forceManyBody().strength(chargeStrength))
      .force('center', d3.forceCenter(currentWidth / 2, currentHeight / 2))
      .force('collision', d3.forceCollide().radius(collisionRadius))
      .alphaDecay(config.alphaDecay)
      .velocityDecay(config.velocityDecay);
    
    // 保存模拟引用
    simulationRef.current = simulation;

    // 创建箭头标记（必须在边之前创建）
    const defs = svg.append('defs');
    defs
      .append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 25)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // 创建边组（必须在节点之前，这样节点会显示在边的上方）
    const linkGroup = g.append('g').attr('class', 'links');
    
    // 判断是否是元模型图（根据节点类型）
    const isMetamodelGraph = nodes.some(n => n.type === 'entity' || n.type === 'collector');
    
    // 创建边
    // 注意：forceLink 会在创建 simulation 时转换 source/target 为节点对象
    // 所以我们需要一个能处理两种情况的 key 函数
    const getLinkKey = (d: any) => {
      if (d.sourceId && d.targetId) {
        return `${d.sourceId}-${d.targetId}`;
      }
      const sourceId = typeof d.source === 'object' ? String(d.source.id) : String(d.source);
      const targetId = typeof d.target === 'object' ? String(d.target.id) : String(d.target);
      return `${sourceId}-${targetId}`;
    };
    
    const link = linkGroup
      .selectAll('line')
      .data(links, getLinkKey)
      .enter()
      .append('line')
      .attr('stroke', (d: any) => {
        // 元模型图：关系元模型使用绿色（与图例一致）
        if (isMetamodelGraph) {
          return '#52c41a'; // 关系元模型 - 绿色
        }
        // 其他图：根据方向设置不同颜色：上游用蓝色，下游用绿色
        if (d.direction === 'upstream') {
          return '#1890ff'; // 蓝色表示上游
        } else if (d.direction === 'downstream') {
          return '#52c41a'; // 绿色表示下游
        }
        return '#999'; // 默认灰色
      })
      .attr('stroke-opacity', 0.8)
      .attr('stroke-width', 2)
      .attr('marker-end', 'url(#arrowhead)');

    // 移除调试信息，避免控制台刷屏

    // 创建边标签（根据配置决定是否显示）
    const linkLabels = linkGroup
      .selectAll('text')
      .data(links)
      .enter()
      .append('text')
      .attr('font-size', '10px')
      .attr('font-family', 'Arial, sans-serif')
      .attr('fill', '#666')
      .attr('text-anchor', 'middle')
      .attr('pointer-events', 'none')
      .style('opacity', showEdgeLabels ? 0.8 : 0) // 如果配置显示，默认显示；否则只在悬停时显示
      .text((d) => d.type || '');

    // 创建节点组
    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g.node')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('cursor', 'pointer')
      .call(
        d3
          .drag<SVGGElement, D3Node>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on('click', (event, d) => {
        event.stopPropagation();
        setSelectedNode(d.id === selectedNode ? null : d.id);
        onNodeClick?.(d);
      })
      .on('mouseenter', (event, d) => {
        onNodeHover?.(d);
        // 高亮相关节点和边
        link
          .transition()
          .duration(200)
          .attr('stroke-opacity', (l: any) => {
            const source = typeof l.source === 'object' ? l.source : nodeMap.get(String(l.source));
            const target = typeof l.target === 'object' ? l.target : nodeMap.get(String(l.target));
            return (source === d || target === d) ? 1 : 0.1;
          })
          .attr('stroke-width', (l: any) => {
            const source = typeof l.source === 'object' ? l.source : nodeMap.get(String(l.source));
            const target = typeof l.target === 'object' ? l.target : nodeMap.get(String(l.target));
            return (source === d || target === d) ? 3 : 2;
          });
        node
          .transition()
          .duration(200)
          .attr('opacity', (n) => {
            return n === d || links.some((l: any) => {
              const source = typeof l.source === 'object' ? l.source : nodeMap.get(String(l.source));
              const target = typeof l.target === 'object' ? l.target : nodeMap.get(String(l.target));
              return (source === d && target === n) || (target === d && source === n);
            }) ? 1 : 0.3;
          });
        // 显示相关边的标签（如果配置显示，则始终显示；否则只在悬停时显示）
        linkLabels
          .transition()
          .duration(200)
          .style('opacity', (l: any) => {
            if (showEdgeLabels) {
              // 如果配置显示，相关边更明显
              const source = typeof l.source === 'object' ? l.source : nodeMap.get(String(l.source));
              const target = typeof l.target === 'object' ? l.target : nodeMap.get(String(l.target));
              return (source === d || target === d) ? 1 : 0.8;
            } else {
              // 如果配置不显示，只在悬停时显示
              const source = typeof l.source === 'object' ? l.source : nodeMap.get(String(l.source));
              const target = typeof l.target === 'object' ? l.target : nodeMap.get(String(l.target));
              return (source === d || target === d) ? 0.8 : 0;
            }
          });
      })
      .on('mouseleave', () => {
        onNodeHover?.(null);
        link
          .transition()
          .duration(200)
          .attr('stroke-opacity', 0.6)
          .attr('stroke-width', 2);
        node
          .transition()
          .duration(200)
          .attr('opacity', 1);
        linkLabels
          .transition()
          .duration(200)
          .style('opacity', showEdgeLabels ? 0.8 : 0); // 如果配置显示，保持显示；否则隐藏
      });

    // 创建节点圆圈（带阴影效果）
    const circles = node
      .append('circle')
      .attr('r', (d) => {
        // 根据节点类型调整大小
        const baseSize = 15;
        const typeMultiplier: Record<string, number> = {
          file: 1.0,
          directory: 1.2,
          function: 0.9,
          class: 1.1,
          table: 1.3,
          default: 1.0,
        };
        return baseSize * (typeMultiplier[d.type] || 1.0);
      })
      .attr('fill', (d) => nodeTypeColors[d.type] || nodeTypeColors.default)
      .attr('stroke', (d) => (d.id === selectedNode ? '#ff4d4f' : '#fff'))
      .attr('stroke-width', (d) => (d.id === selectedNode ? 3 : 2))
      .style('filter', 'drop-shadow(2px 2px 4px rgba(0,0,0,0.2))')
      .on('mouseenter', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', (d) => {
            const baseSize = 15;
            const typeMultiplier: Record<string, number> = {
              file: 1.0,
              directory: 1.2,
              function: 0.9,
              class: 1.1,
              table: 1.3,
              default: 1.0,
            };
            return baseSize * (typeMultiplier[d.type] || 1.0) * 1.3;
          })
          .style('filter', 'drop-shadow(4px 4px 8px rgba(0,0,0,0.4))');
      })
      .on('mouseleave', function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr('r', (d) => {
            const baseSize = 15;
            const typeMultiplier: Record<string, number> = {
              file: 1.0,
              directory: 1.2,
              function: 0.9,
              class: 1.1,
              table: 1.3,
              default: 1.0,
            };
            return baseSize * (typeMultiplier[d.type] || 1.0);
          })
          .style('filter', 'drop-shadow(2px 2px 4px rgba(0,0,0,0.2))');
      });

    // 创建节点标签 - 根据配置决定是否显示
    if (showNodeLabels || nodeCount < graphConfig.hideLabelsThreshold) {
      const labels = node
        .append('text')
        .text((d) => d.label || d.id)
        .attr('font-size', '12px')
        .attr('font-family', 'Arial, sans-serif')
        .attr('fill', '#333')
        .attr('dx', 20)
        .attr('dy', 5)
        .attr('pointer-events', 'none')
        .style('opacity', showNodeLabels ? 1 : (nodeCount < graphConfig.hideLabelsThreshold ? 1 : 0));

      // 创建节点类型标签
      node
        .append('text')
        .text((d) => `[${d.type}]`)
        .attr('font-size', '10px')
        .attr('font-family', 'Arial, sans-serif')
        .attr('fill', '#999')
        .attr('dx', 20)
        .attr('dy', 20)
        .attr('pointer-events', 'none')
        .style('opacity', showNodeLabels ? 1 : (nodeCount < graphConfig.hideLabelsThreshold ? 1 : 0));
    }

    // 创建标签显示（如果有标签）- 性能优化：仅在节点数量较少时显示（使用配置值）
    if (nodeCount < graphConfig.hideLabelsThreshold) {
      const tagGroups = node
        .filter((d) => d.tags && d.tags.length > 0)
        .append('g')
        .attr('class', 'tags')
        .attr('transform', 'translate(20, 35)');

      tagGroups.each(function(d: any) {
        const tagGroup = d3.select(this);
        const tags = d.tags || [];
        const firstTag = tags[0];
        if (firstTag) {
          // 只显示第一个标签，避免图太拥挤
          const tagRect = tagGroup
            .append('rect')
            .attr('width', (firstTag.name || firstTag.tag_name || '').length * 7 + 8)
            .attr('height', 16)
            .attr('rx', 3)
            .attr('fill', firstTag.color || '#1890ff')
            .attr('opacity', 0.8);
          
          const tagText = tagGroup
            .append('text')
            .text(firstTag.name || firstTag.tag_name || '')
            .attr('font-size', '10px')
            .attr('font-family', 'Arial, sans-serif')
            .attr('fill', '#fff')
            .attr('dx', 4)
            .attr('dy', 12)
            .attr('pointer-events', 'none');
          
          // 如果有多个标签，显示数量
          if (tags.length > 1) {
            const countText = tagGroup
              .append('text')
              .text(`+${tags.length - 1}`)
              .attr('font-size', '9px')
              .attr('font-family', 'Arial, sans-serif')
              .attr('fill', '#666')
              .attr('dx', (firstTag.name || firstTag.tag_name || '').length * 7 + 12)
              .attr('dy', 12)
              .attr('pointer-events', 'none');
          }
        }
      });
    }

    // 更新位置函数 - 性能优化：使用requestAnimationFrame节流
    const ticked = () => {
      const now = performance.now();
      // 限制更新频率到60fps
      if (now - lastUpdateRef.current < 16) {
        return;
      }
      lastUpdateRef.current = now;

      // 取消之前的raf
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }

      rafRef.current = requestAnimationFrame(() => {
        // 更新边的位置
        link
          .attr('x1', (d: any) => {
            const source = typeof d.source === 'object' ? d.source : nodeMap.get(String(d.source));
            return (source as D3Node)?.x ?? 0;
          })
          .attr('y1', (d: any) => {
            const source = typeof d.source === 'object' ? d.source : nodeMap.get(String(d.source));
            return (source as D3Node)?.y ?? 0;
          })
          .attr('x2', (d: any) => {
            const target = typeof d.target === 'object' ? d.target : nodeMap.get(String(d.target));
            return (target as D3Node)?.x ?? 0;
          })
          .attr('y2', (d: any) => {
            const target = typeof d.target === 'object' ? d.target : nodeMap.get(String(d.target));
            return (target as D3Node)?.y ?? 0;
          });

        // 更新边标签位置（仅在节点数量较少时，使用配置值）
        if (nodeCount < graphConfig.hideLabelsThreshold) {
          linkLabels
            .attr('x', (d: any) => {
              const source = typeof d.source === 'object' ? d.source : nodeMap.get(String(d.source));
              const target = typeof d.target === 'object' ? d.target : nodeMap.get(String(d.target));
              return (((source as D3Node)?.x ?? 0) + ((target as D3Node)?.x ?? 0)) / 2;
            })
            .attr('y', (d: any) => {
              const source = typeof d.source === 'object' ? d.source : nodeMap.get(String(d.source));
              const target = typeof d.target === 'object' ? d.target : nodeMap.get(String(d.target));
              return (((source as D3Node)?.y ?? 0) + ((target as D3Node)?.y ?? 0)) / 2;
            });
        }

        node.attr('transform', (d) => `translate(${d.x || 0},${d.y || 0})`);
        rafRef.current = null;
      });
    };

    // 启动模拟
    simulation.on('tick', ticked);

    // 点击空白处取消选择
    svg.on('click', () => {
      setSelectedNode(null);
    });

    // 清理函数
    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
        simulationRef.current = null;
      }
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      svg.on('click', null);
    };
  }, [data.nodes.length, data.edges.length, dimensions.width, dimensions.height, selectedNode, showNodeLabels, showEdgeLabels, maxNodes, maxEdges, onNodeClick, onNodeHover]);

  return (
    <div 
      ref={containerRef} 
      style={{ 
        width: '100%', 
        height: '100%', 
        position: 'relative',
        minHeight: 0,
        overflow: 'hidden'
      }}
    >
      <svg 
        ref={svgRef} 
        width={dimensions.width} 
        height={dimensions.height} 
        style={{ 
          border: '1px solid #d9d9d9', 
          borderRadius: '4px',
          display: 'block',
          maxWidth: '100%',
          maxHeight: '100%'
        }}
      >
        {/* SVG 内容由 D3 动态生成 */}
      </svg>
    </div>
  );
}

