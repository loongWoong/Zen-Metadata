/**
 * 层次布局组件
 * 用于展示系统 → 表 → 字段等层次结构
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { Tag, Space, Card, Button, Tooltip } from 'antd';
import { ExpandOutlined, CompressOutlined } from '@ant-design/icons';
import type { GraphData, GraphNode, GraphEdge } from '../../types';

interface HierarchyLayoutProps {
  data: GraphData;
  width?: number;
  height?: number;
  maxNodes?: number;
  maxEdges?: number;
  onNodeClick?: (node: GraphNode) => void;
  onNodeHover?: (node: GraphNode | null) => void;
}

export default function HierarchyLayout({
  data,
  width = 1000,
  height = 600,
  maxNodes,
  maxEdges,
  onNodeClick,
  onNodeHover,
}: HierarchyLayoutProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const overviewRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width, height });
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  const [contentBounds, setContentBounds] = useState({ minX: 0, maxX: 0, minY: 0, maxY: 0 });
  const [rootNodes, setRootNodes] = useState<Array<{ node: GraphNode; position: { x: number; y: number } }>>([]);
  const [showLegend, setShowLegend] = useState(true);
  const [defaultExpandAll, setDefaultExpandAll] = useState(true); // 默认展开所有节点
  const [allNodeIds, setAllNodeIds] = useState<Set<string>>(new Set()); // 存储所有节点ID（用于批量操作）
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const svgElementRef = useRef<SVGSVGElement | null>(null);
  const dataKeyRef = useRef<string>('');
  const defaultExpandAllRef = useRef<boolean>(true); // 用于跟踪 defaultExpandAll 的变化
  const isUpdatingCollapsedRef = useRef<boolean>(false); // 防止循环更新

  // 当数据变化时，重置折叠状态
  useEffect(() => {
    const currentDataKey = `${data.nodes.length}-${data.edges.length}`;
    if (dataKeyRef.current !== currentDataKey) {
      dataKeyRef.current = currentDataKey;
      setCollapsedNodes(new Set());
    }
  }, [data.nodes.length, data.edges.length]);

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

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // 设置SVG尺寸为容器尺寸
    const actualWidth = dimensions.width;
    const actualHeight = dimensions.height;
    svg.attr('width', actualWidth).attr('height', actualHeight);

    const g = svg.append('g');

    // 应用限制配置（与力导向布局保持一致的数据过滤逻辑）
    // 优先限制节点数，然后过滤边，最后再限制边数
    const nodeLimit = maxNodes || Infinity;
    const edgeLimit = maxEdges || Infinity;
    
    let displayNodes = data.nodes;
    let displayEdges = data.edges;
    
    // 第一步：限制节点数
    if (data.nodes.length > nodeLimit) {
      displayNodes = data.nodes.slice(0, nodeLimit);
      // 只保留与显示节点相关的边
      const nodeIdSet = new Set(displayNodes.map(n => String(n.id)));
      displayEdges = data.edges.filter(edge => {
        const sourceId = String(edge.source);
        const targetId = String(edge.target);
        return nodeIdSet.has(sourceId) && nodeIdSet.has(targetId);
      });
      
      // 数据截断是预期行为，不输出警告
    }
    
    // 第二步：限制边数（在节点过滤后的基础上）
    if (displayEdges.length > edgeLimit) {
      displayEdges = displayEdges.slice(0, edgeLimit);
      // 只保留与显示边相关的节点
      const edgeNodeIds = new Set<string>();
      displayEdges.forEach(edge => {
        edgeNodeIds.add(String(edge.source));
        edgeNodeIds.add(String(edge.target));
      });
      displayNodes = displayNodes.filter(n => edgeNodeIds.has(String(n.id)));
      
      // 数据截断是预期行为，不输出警告
    }

    // 创建树形层次结构
    const root = buildHierarchy(displayNodes, displayEdges);
    
    // 计算合适的节点间距，防止重叠
    // 基础节点高度，包括节点圆圈、文本和间距
    const baseNodeHeight = 60; // 非末尾层级的节点间距
    const leafNodeHeight = 45; // 最末尾层级（叶子节点）的间距（减少间距，但不重叠）
    const nodeWidth = 150; // 每个节点占用的水平空间（包括文本）
    const maxDepth = getMaxDepth(root);
    
    // 动态计算布局尺寸，确保节点不重叠
    const layoutHeight = Math.max(actualHeight - 100, maxDepth * baseNodeHeight);
    const layoutWidth = Math.max(actualWidth - 200, 300);
    
    const treeLayout = d3.tree<HierarchyNode>()
      .nodeSize([baseNodeHeight, nodeWidth])
      .separation((a, b) => {
        // 兄弟节点之间的间距
        if (a.parent === b.parent) {
          // 如果是同一父节点的兄弟节点
          // 检查是否是叶子节点（最末尾层级）
          const aIsLeaf = !a.children || a.children.length === 0;
          const bIsLeaf = !b.children || b.children.length === 0;
          
          // 如果都是叶子节点，使用较小的间距
          if (aIsLeaf && bIsLeaf) {
            return leafNodeHeight / baseNodeHeight; // 约 0.75，减少间距但不重叠
          }
          return 1.2; // 非叶子节点保持较大间距
        }
        return 1;
      });

    const rootNode = d3.hierarchy(root);
    
    // 识别根节点ID（用于区分根节点和非根节点）
    const rootNodeIds = new Set<string>();
    if (root.id === '__virtual_root__' && rootNode.children) {
      rootNode.children.forEach((child: any) => {
        if (child.data && child.data.id !== '__virtual_root__') {
          rootNodeIds.add(child.data.id);
        }
      });
    } else {
      rootNode.each((d: any) => {
        if (d.depth === 0 && d.data && d.data.id !== '__virtual_root__') {
          rootNodeIds.add(d.data.id);
        }
      });
    }
    
    // 根据默认展开状态，自动设置折叠状态（在应用折叠状态之前）
    // 使用当前的 collapsedNodes 作为基础，根据 defaultExpandAll 调整
    let nodesToCollapse = new Set(collapsedNodes);
    
    // 只在 defaultExpandAll 改变时才调整折叠状态
    const defaultExpandAllChanged = defaultExpandAllRef.current !== defaultExpandAll;
    if (defaultExpandAllChanged) {
      defaultExpandAllRef.current = defaultExpandAll;
      
      if (!defaultExpandAll) {
        // 如果默认折叠，则折叠所有非根节点（有子节点的）
        rootNode.each((d: any) => {
          // 跳过根节点和虚拟根节点，只折叠有子节点的非根节点
          if (d.data && d.data.id !== '__virtual_root__' && !rootNodeIds.has(d.data.id) && d.children && d.children.length > 0) {
            nodesToCollapse.add(d.data.id);
          }
        });
      } else {
        // 如果默认展开，清除所有非根节点的折叠状态（保留根节点的手动折叠状态）
        rootNode.each((d: any) => {
          if (d.data && d.data.id !== '__virtual_root__' && !rootNodeIds.has(d.data.id)) {
            nodesToCollapse.delete(d.data.id);
          }
        });
      }
      
      // 只在真正改变时才更新状态
      const collapsedArray = Array.from(nodesToCollapse).sort();
      const currentCollapsedArray = Array.from(collapsedNodes).sort();
      const collapsedChanged = collapsedArray.length !== currentCollapsedArray.length ||
        collapsedArray.some((id, i) => id !== currentCollapsedArray[i]);
      
      if (collapsedChanged && !isUpdatingCollapsedRef.current) {
        isUpdatingCollapsedRef.current = true;
        setCollapsedNodes(nodesToCollapse);
        // 重置标志，但延迟一下避免立即触发
        setTimeout(() => {
          isUpdatingCollapsedRef.current = false;
        }, 100);
      }
    }
    
    // 应用折叠状态
    rootNode.each((d: any) => {
      if (nodesToCollapse.has(d.data.id)) {
        d._children = d.children;
        d.children = null;
      }
    });
    
    treeLayout(rootNode);

    // 计算布局边界，用于居中显示
    const bounds = getLayoutBounds(rootNode);
    const dx = (actualWidth - bounds.width) / 2 - bounds.x;
    const dy = (actualHeight - bounds.height) / 2 - bounds.y;

    // 存储节点位置信息，用于绘制鹰眼（过滤掉虚拟根节点）
    const nodePositions = new Map<string, { x: number; y: number }>();
    rootNode.each((d: any) => {
      if (d.data.id !== '__virtual_root__') {
        nodePositions.set(d.data.id, { x: d.y, y: d.x });
      }
    });

    // 更新内容边界
    setContentBounds({
      minX: bounds.x,
      maxX: bounds.x + bounds.width,
      minY: bounds.y,
      maxY: bounds.y + bounds.height,
    });

    // 识别顶级节点（根节点）并存储其位置
    const topLevelNodes: Array<{ node: GraphNode; position: { x: number; y: number } }> = [];
    
    // 检查是否有虚拟根节点（root 是 HierarchyNode，直接访问 id）
    if (root.id === '__virtual_root__' && rootNode.children) {
      // 如果有虚拟根节点，获取其直接子节点（真正的根节点）
      rootNode.children.forEach((child: any) => {
        if (child.data && child.data.id !== '__virtual_root__') {
          topLevelNodes.push({
            node: child.data as GraphNode,
            position: { x: child.y, y: child.x }
          });
        }
      });
    } else {
      // 只有一个根节点，或者没有虚拟根节点
      rootNode.each((d: any) => {
        if (d.depth === 0 && d.data && d.data.id !== '__virtual_root__') {
          topLevelNodes.push({
            node: d.data as GraphNode,
            position: { x: d.y, y: d.x }
          });
        }
      });
    }
    
    setRootNodes(topLevelNodes);
    
    // 收集所有节点ID（用于批量展开/折叠）
    const allIds = new Set<string>();
    rootNode.each((d: any) => {
      if (d.data && d.data.id !== '__virtual_root__') {
        allIds.add(d.data.id);
      }
    });
    setAllNodeIds(allIds);
    
    // 不再在这里更新 collapsedNodes，避免循环
    // collapsedNodes 的更新已经在上面处理了

    // 更新鹰眼视图函数（需要在 zoom 定义之前声明）
    let currentTransform = d3.zoomIdentity;
    const updateOverview = () => {
      if (!overviewRef.current || nodePositions.size === 0) return;
      
      const overviewSvg = d3.select(overviewRef.current);
      overviewSvg.selectAll('*').remove();
      
      const overviewWidth = 200;
      const overviewHeight = 150;
      
      // 计算缩放比例
      const contentWidth = bounds.width;
      const contentHeight = bounds.height;
      const scaleX = overviewWidth / contentWidth;
      const scaleY = overviewHeight / contentHeight;
      const scale = Math.min(scaleX, scaleY); // 保持宽高比
      
      // 绘制缩略图背景
      overviewSvg
        .append('rect')
        .attr('width', overviewWidth)
        .attr('height', overviewHeight)
        .attr('fill', '#f5f5f5')
        .attr('stroke', '#d9d9d9');
      
      // 绘制所有节点（简化版）
      const overviewG = overviewSvg.append('g');
      const offsetX = (overviewWidth - contentWidth * scale) / 2;
      const offsetY = (overviewHeight - contentHeight * scale) / 2;
      
      nodePositions.forEach((pos) => {
        overviewG
          .append('circle')
          .attr('cx', offsetX + (pos.x - bounds.x) * scale)
          .attr('cy', offsetY + (pos.y - bounds.y) * scale)
          .attr('r', 1.5)
          .attr('fill', '#1890ff')
          .attr('opacity', 0.6);
      });
      
      // 计算当前视图框在鹰眼中的位置和尺寸
      // 主视图的可见区域在树形布局坐标系中的尺寸
      const viewBoxWidth = (actualWidth / currentTransform.k) * scale;
      const viewBoxHeight = (actualHeight / currentTransform.k) * scale;
      
      // 计算视图框左上角在树形布局坐标系中的位置
      // currentTransform.x 和 currentTransform.y 是 SVG 坐标系的平移量
      // 需要转换为树形布局坐标系
      const viewTopLeftX = (-currentTransform.x / currentTransform.k);
      const viewTopLeftY = (-currentTransform.y / currentTransform.k);
      
      // 转换为鹰眼坐标（相对于 bounds）
      let viewBoxX = offsetX + (viewTopLeftX - bounds.x) * scale;
      let viewBoxY = offsetY + (viewTopLeftY - bounds.y) * scale;
      
      // 确保视图框不超出鹰眼边界
      viewBoxX = Math.max(0, Math.min(viewBoxX, overviewWidth - viewBoxWidth));
      viewBoxY = Math.max(0, Math.min(viewBoxY, overviewHeight - viewBoxHeight));
      
      // 确保宽度和高度都是正值
      const finalWidth = Math.max(0, Math.min(viewBoxWidth, overviewWidth - viewBoxX));
      const finalHeight = Math.max(0, Math.min(viewBoxHeight, overviewHeight - viewBoxY));
      
      // 只有当视图框有效时才绘制
      if (finalWidth > 0 && finalHeight > 0) {
        const viewBoxRect = overviewG
          .append('rect')
          .attr('x', viewBoxX)
          .attr('y', viewBoxY)
          .attr('width', finalWidth)
          .attr('height', finalHeight)
          .attr('fill', 'rgba(255, 77, 79, 0.2)')
          .attr('stroke', '#ff4d4f')
          .attr('stroke-width', 2)
          .style('cursor', 'move');
        
        // 添加拖动功能来移动视图
        let dragStartX = 0;
        let dragStartY = 0;
        let dragStartTransform = currentTransform;
        
        viewBoxRect.call(
          d3.drag<SVGRectElement, unknown>()
            .on('start', (event) => {
              // 记录拖动开始时的位置和变换
              const point = d3.pointer(event, overviewRef.current);
              dragStartX = point[0];
              dragStartY = point[1];
              dragStartTransform = currentTransform;
            })
            .on('drag', (event) => {
              // 计算拖动距离（在鹰眼坐标系中）
              const point = d3.pointer(event, overviewRef.current);
              const deltaX = point[0] - dragStartX;
              const deltaY = point[1] - dragStartY;
              
              // 将拖动距离转换为主视图的平移量
              // 拖动距离在鹰眼坐标系中，需要转换为树形布局坐标系，再转换为 SVG 坐标系
              const deltaMainX = -deltaX * currentTransform.k / scale;
              const deltaMainY = -deltaY * currentTransform.k / scale;
              
              // 计算新的变换
              const newTransform = d3.zoomIdentity
                .translate(
                  dragStartTransform.x + deltaMainX,
                  dragStartTransform.y + deltaMainY
                )
                .scale(dragStartTransform.k);
              
              // 应用新变换
              svg.call(zoom.transform, newTransform);
            })
        );
      }
    };

    // 创建缩放和平移
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        currentTransform = event.transform;
        g.attr('transform', event.transform);
        updateOverview();
      });

    svg.call(zoom);
    zoomRef.current = zoom;
    svgElementRef.current = svgRef.current;

    // 初始居中显示
    const initialTransform = d3.zoomIdentity
      .translate(dx, dy)
      .scale(1);
    currentTransform = initialTransform;
    svg.call(zoom.transform, initialTransform);
    
    // 初始更新鹰眼（延迟一下确保DOM已渲染）
    setTimeout(() => {
      updateOverview();
    }, 100);

    // 绘制边（过滤掉与虚拟根节点相关的边）
    const links = g
      .append('g')
      .attr('class', 'links')
      .selectAll('path')
      .data(rootNode.links().filter((d: any) => {
        const source = d.source as any;
        const target = d.target as any;
        // 过滤掉虚拟根节点的边
        return source.data.id !== '__virtual_root__' && target.data.id !== '__virtual_root__';
      }))
      .enter()
      .append('path')
      .attr('d', (d) => {
        const source = d.source as any;
        const target = d.target as any;
        return `M${source.y},${source.x}L${target.y},${target.x}`;
      })
      .attr('fill', 'none')
      .attr('stroke', '#999')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.6);

    // 绘制节点（过滤掉虚拟根节点）
    const nodes = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g.node')
      .data(rootNode.descendants().filter((d: any) => d.data.id !== '__virtual_root__'))
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('transform', (d) => `translate(${(d as any).y},${(d as any).x})`)
      .style('cursor', 'pointer')
      .on('click', (event, d: any) => {
        // 如果点击的是展开/折叠图标，事件已经被图标处理了，这里不处理
        const target = event.target as SVGElement;
        if (target.closest('.expand-collapse')) {
          return;
        }
        
        event.stopPropagation();
        // 点击节点本身，触发节点详情
        onNodeClick?.(d.data as GraphNode);
      })
      .on('mouseenter', (event, d) => {
        d3.select(event.currentTarget)
          .select('circle')
          .attr('r', 12)
          .attr('stroke-width', 3);
        onNodeHover?.(d.data as GraphNode);
      })
      .on('mouseleave', (event) => {
        d3.select(event.currentTarget)
          .select('circle')
          .attr('r', 10)
          .attr('stroke-width', 2);
        onNodeHover?.(null);
      });

    // 绘制节点圆圈
    nodes
      .append('circle')
      .attr('r', 10)
      .attr('fill', '#1890ff')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);
    
    // 绘制展开/折叠图标（只对有子节点的节点显示）
    nodes.each(function(d: any) {
      if (d.children || d._children) {
        const iconGroup = d3.select(this)
          .append('g')
          .attr('class', 'expand-collapse')
          .attr('transform', 'translate(-15, 0)')
          .style('cursor', 'pointer')
          .on('click', (event) => {
            event.stopPropagation();
            const isCollapsed = d.children === null;
            if (isCollapsed) {
              // 展开
              setCollapsedNodes(prev => {
                const newSet = new Set(prev);
                newSet.delete(d.data.id);
                return newSet;
              });
            } else {
              // 折叠
              setCollapsedNodes(prev => {
                const newSet = new Set(prev);
                newSet.add(d.data.id);
                return newSet;
              });
            }
          });
        
        iconGroup
          .append('circle')
          .attr('r', 8)
          .attr('fill', '#fff')
          .attr('stroke', '#1890ff')
          .attr('stroke-width', 2);
        
        iconGroup
          .append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', '0.35em')
          .attr('font-size', '10px')
          .attr('fill', '#1890ff')
          .attr('font-weight', 'bold')
          .text(d.children ? '−' : '+');
      }
    });

    // 节点文本，使用背景矩形防止重叠
    const textGroups = nodes
      .append('g')
      .attr('class', 'text-group');

    textGroups
      .append('rect')
      .attr('x', 15)
      .attr('y', -8)
      .attr('width', (d) => {
        const text = (d.data as GraphNode).label || (d.data as GraphNode).id;
        return Math.min(text.length * 7 + 8, 140);
      })
      .attr('height', 16)
      .attr('fill', 'rgba(255, 255, 255, 0.9)')
      .attr('stroke', '#d9d9d9')
      .attr('stroke-width', 1)
      .attr('rx', 2);

    textGroups
      .append('text')
      .attr('dx', 19)
      .attr('dy', 5)
      .text((d) => {
        const text = (d.data as GraphNode).label || (d.data as GraphNode).id;
        // 如果文本太长，截断并添加省略号
        return text.length > 20 ? text.substring(0, 20) + '...' : text;
      })
      .attr('font-size', '12px')
      .attr('fill', '#333')
      .attr('pointer-events', 'none');
  }, [data, dimensions, maxNodes, maxEdges, collapsedNodes, defaultExpandAll, onNodeClick, onNodeHover]);

  // 判断是否需要显示鹰眼（内容超出可视区域）
  const showOverview = contentBounds.maxX - contentBounds.minX > dimensions.width || 
                       contentBounds.maxY - contentBounds.minY > dimensions.height;

  // 切换默认展开/折叠状态
  const toggleDefaultExpand = useCallback(() => {
    setDefaultExpandAll(prev => !prev);
    // 状态改变会触发useEffect重新渲染，在useEffect中处理实际的展开/折叠逻辑
  }, []);

  // 跳转到指定节点位置
  const jumpToNode = useCallback((nodePosition: { x: number; y: number }) => {
    if (!svgElementRef.current || !zoomRef.current) return;
    
    const svg = d3.select(svgElementRef.current);
    
    // 节点位置在树形布局坐标系中（d3.tree 的坐标系）
    // d3.tree 使用 (y, x) 坐标，其中 y 是水平位置，x 是垂直位置
    const targetX = nodePosition.x; // 树形布局的水平位置
    const targetY = nodePosition.y; // 树形布局的垂直位置
    
    // 获取SVG尺寸
    const svgWidth = dimensions.width;
    const svgHeight = dimensions.height;
    
    // 计算需要平移的距离，使节点居中显示
    const centerX = svgWidth / 2;
    const centerY = svgHeight / 2;
    
    // 计算变换，使目标节点居中
    // 注意：d3.tree 的坐标系统是 (y, x)，所以这里需要对应
    const newTransform = d3.zoomIdentity
      .translate(centerX - targetX, centerY - targetY)
      .scale(1);
    
    // 应用变换，使用过渡动画
    svg.transition()
      .duration(500)
      .ease(d3.easeCubicOut)
      .call(zoomRef.current.transform, newTransform);
  }, [dimensions.width, dimensions.height]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
      <svg 
        ref={svgRef} 
        width={dimensions.width} 
        height={dimensions.height} 
        style={{ 
          border: '1px solid #d9d9d9',
          display: 'block'
        }} 
      />
      
      {/* 顶级节点图例 */}
      {showLegend && rootNodes.length > 0 && (
        <Card
          size="small"
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 'bold' }}>顶级节点 ({rootNodes.length})</span>
              <span
                onClick={() => setShowLegend(false)}
                style={{ cursor: 'pointer', fontSize: '12px', color: '#999' }}
              >
                ×
              </span>
            </div>
          }
          style={{
            position: 'absolute',
            top: 8,
            left: 8,
            zIndex: 10,
            maxWidth: '300px',
            maxHeight: '400px',
            overflow: 'auto'
          }}
          styles={{
            body: {
              padding: '8px'
            }
          }}
        >
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            {/* 展开/折叠控制按钮 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '4px', borderBottom: '1px solid #f0f0f0', marginBottom: '4px' }}>
              <span style={{ fontSize: '11px', color: '#666' }}>子节点状态:</span>
              <Tooltip title={defaultExpandAll ? '点击折叠所有子节点' : '点击展开所有子节点'}>
                <Button
                  type={defaultExpandAll ? 'default' : 'primary'}
                  size="small"
                  icon={defaultExpandAll ? <CompressOutlined /> : <ExpandOutlined />}
                  onClick={toggleDefaultExpand}
                  style={{ fontSize: '11px', height: '24px', padding: '0 8px' }}
                >
                  {defaultExpandAll ? '全部展开' : '全部折叠'}
                </Button>
              </Tooltip>
            </div>
            
            {/* 顶级节点列表 */}
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              {rootNodes.map(({ node, position }) => (
                <Tag
                  key={node.id}
                  color="blue"
                  onClick={() => jumpToNode(position)}
                  style={{
                    cursor: 'pointer',
                    margin: 0,
                    padding: '4px 8px',
                    fontSize: '11px',
                    maxWidth: '100%',
                    display: 'block',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#1890ff';
                    e.currentTarget.style.color = '#fff';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = '';
                    e.currentTarget.style.color = '';
                  }}
                >
                  {node.label || node.id}
                </Tag>
              ))}
            </Space>
          </Space>
        </Card>
      )}
      
      {/* 显示图例按钮（当图例隐藏时） */}
      {!showLegend && rootNodes.length > 0 && (
        <div
          onClick={() => setShowLegend(true)}
          style={{
            position: 'absolute',
            top: 8,
            left: 8,
            zIndex: 10,
            background: 'rgba(255, 255, 255, 0.9)',
            padding: '4px 8px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '11px',
            color: '#1890ff',
            border: '1px solid #d9d9d9',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}
        >
          显示图例
        </div>
      )}
      
      {/* 鹰眼视图（预览区域控制） */}
      {showOverview && (
        <div style={{
          position: 'absolute',
          bottom: 8,
          right: 8,
          zIndex: 10,
          background: 'rgba(255, 255, 255, 0.95)',
          padding: '8px',
          borderRadius: '4px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          border: '1px solid #d9d9d9'
        }}>
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px', fontWeight: 'bold' }}>
            鹰眼视图
          </div>
          <svg
            ref={overviewRef}
            width={200}
            height={150}
            style={{ display: 'block', border: '1px solid #e8e8e8', borderRadius: '2px' }}
          />
        </div>
      )}
    </div>
  );
}

interface HierarchyNode {
  id: string;
  label: string;
  type: string;
  children?: HierarchyNode[];
  [key: string]: any;
}

function buildHierarchy(nodes: GraphNode[], edges: GraphEdge[]): HierarchyNode {
  // 找到根节点（没有入边的节点）
  const nodeMap = new Map<string, GraphNode>();
  const inDegree = new Map<string, number>();

  nodes.forEach((node) => {
    nodeMap.set(node.id, node);
    inDegree.set(node.id, 0);
  });

  edges.forEach((edge) => {
    const count = inDegree.get(edge.target) || 0;
    inDegree.set(edge.target, count + 1);
  });

  // 找到所有根节点
  const rootNodes = nodes.filter((node) => (inDegree.get(node.id) || 0) === 0);
  
  // 如果没有根节点，使用第一个节点作为根
  if (rootNodes.length === 0) {
    rootNodes.push(nodes[0]);
  }

  // 构建树结构
  const buildTree = (nodeId: string): HierarchyNode => {
    const node = nodeMap.get(nodeId)!;
    const children: HierarchyNode[] = [];

    edges.forEach((edge) => {
      if (edge.source === nodeId) {
        children.push(buildTree(edge.target));
      }
    });

    return {
      ...node,
      children: children.length > 0 ? children : undefined,
    };
  };

  // 如果有多个根节点，创建一个虚拟根节点来包含所有根节点
  if (rootNodes.length > 1) {
    const virtualRoot: HierarchyNode = {
      id: '__virtual_root__',
      label: 'Root',
      type: 'virtual',
      children: rootNodes.map(root => buildTree(root.id)),
    };
    return virtualRoot;
  }

  // 只有一个根节点，直接返回
  return buildTree(rootNodes[0].id);
}

// 获取树的最大深度
function getMaxDepth(node: HierarchyNode, depth = 0): number {
  if (!node.children || node.children.length === 0) {
    return depth;
  }
  return Math.max(...node.children.map(child => getMaxDepth(child, depth + 1)));
}

// 获取布局边界
function getLayoutBounds(root: d3.HierarchyNode<HierarchyNode>) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  root.each((d: any) => {
    if (d.x < minX) minX = d.x;
    if (d.x > maxX) maxX = d.x;
    if (d.y < minY) minY = d.y;
    if (d.y > maxY) maxY = d.y;
  });

  return {
    x: minY,
    y: minX,
    width: maxY - minY,
    height: maxX - minX,
  };
}


