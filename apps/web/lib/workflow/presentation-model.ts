export type WorkflowNodeKind = "source" | "stage" | "resource" | "terminal";

export type WorkflowNode = {
  id: string;
  entityId: string;
  kind: WorkflowNodeKind;
  label: string;
  row: number;
  column: number;
  lane: string;
  order: number;
  resourceIds: string[];
  selectable: true;
  description: string;
};

export type WorkflowEdge = {
  id: string;
  routeId: string;
  fromId: string;
  toId: string;
  routeType: "entry" | "success" | "failure";
  probability: number | null;
  label: string;
  rework: boolean;
  path: string;
  description: string;
};

export type WorkflowResourceLink = { id: string; resourceId: string; stageId: string };
export type WorkflowPresentation = { valid: boolean; nodes: WorkflowNode[]; edges: WorkflowEdge[]; resourceLinks: WorkflowResourceLink[]; warnings: string[] };

type Source = { id: string; name?: string; firstStageId: string; arrival?: Record<string, unknown> };
type Stage = { id: string; name?: string; resourcePoolId?: string; processingTime?: Record<string, unknown>; failure?: { routeId?: string; probability?: number; maximumReworkAttempts?: number } };
type RouteOption = { targetType: string; targetId?: string; probability?: number };
type Route = { id: string; kind: string; fromStageId: string; options: RouteOption[] };
type ResourcePool = { id: string; name?: string; capacity?: number };
export type WorkflowOperationalModel = { sources: Source[]; stages: Stage[]; routes: Route[]; resourcePools: ResourcePool[]; slaRules?: { id: string; targetDuration?: number }[] };

const positions: Record<string, Pick<WorkflowNode, "row" | "column" | "lane" | "order">> = {
  "incoming-tickets": { row: 0, column: 2, lane: "entry", order: 0 },
  triage: { row: 1, column: 2, lane: "primary", order: 1 },
  "level-1": { row: 2, column: 1, lane: "standard", order: 2 },
  "level-2": { row: 2, column: 3, lane: "escalated", order: 3 },
  "quality-check": { row: 3, column: 2, lane: "quality", order: 4 },
  "terminal:quality-resolved:0": { row: 4, column: 2, lane: "terminal", order: 5 },
  "triage-team": { row: 1, column: 4, lane: "resources", order: 6 },
  "level-1-agents": { row: 2, column: 0, lane: "resources", order: 7 },
  "level-2-agents": { row: 2, column: 4, lane: "resources", order: 8 },
  "quality-team": { row: 3, column: 4, lane: "resources", order: 9 },
};

function positionFor(id: string, fallbackOrder: number) {
  return positions[id] ?? { row: fallbackOrder, column: 2, lane: "fallback", order: 100 + fallbackOrder };
}

function point(node: WorkflowNode) {
  return { x: 100 + node.column * 200, y: 65 + node.row * 120 };
}

function edgePath(from: WorkflowNode, to: WorkflowNode, rework: boolean) {
  const start = point(from); const end = point(to);
  if (rework) return `M ${start.x} ${start.y} C ${start.x + 170} ${start.y + 40}, ${end.x + 170} ${end.y + 40}, ${end.x} ${end.y}`;
  const middle = (start.y + end.y) / 2;
  return `M ${start.x} ${start.y} C ${start.x} ${middle}, ${end.x} ${middle}, ${end.x} ${end.y}`;
}

export function buildWorkflowPresentation(model: WorkflowOperationalModel | null | undefined): WorkflowPresentation {
  if (!model) return { valid: false, nodes: [], edges: [], resourceLinks: [], warnings: ["Baseline workflow is unavailable."] };
  const nodes: WorkflowNode[] = []; const edges: WorkflowEdge[] = []; const resourceLinks: WorkflowResourceLink[] = []; const warnings: string[] = [];
  const ids = new Set<string>();
  const addNode = (node: WorkflowNode) => {
    if (ids.has(node.id)) { warnings.push(`Duplicate visual ID ${node.id}.`); return; }
    ids.add(node.id); nodes.push(node);
  };
  const addEdge = (edge: WorkflowEdge) => {
    if (ids.has(edge.id)) { warnings.push(`Duplicate visual ID ${edge.id}.`); return; }
    ids.add(edge.id); edges.push(edge);
  };
  const addResourceLink = (link: WorkflowResourceLink) => {
    if (ids.has(link.id)) { warnings.push(`Duplicate visual ID ${link.id}.`); return; }
    ids.add(link.id); resourceLinks.push(link);
  };

  model.sources.forEach((source, index) => {
    const position = positionFor(source.id, index);
    addNode({ id: source.id, entityId: source.id, kind: "source", label: source.name ?? source.id, ...position, resourceIds: [], selectable: true, description: `${source.name ?? source.id}, source entering at ${source.firstStageId}.` });
  });
  model.stages.forEach((stage, index) => {
    const position = positionFor(stage.id, model.sources.length + index);
    addNode({ id: stage.id, entityId: stage.id, kind: "stage", label: stage.name ?? stage.id, ...position, resourceIds: stage.resourcePoolId ? [stage.resourcePoolId] : [], selectable: true, description: `${stage.name ?? stage.id}, stage${stage.resourcePoolId ? ` supported by ${stage.resourcePoolId}` : ""}.` });
  });

  model.routes.forEach((route) => route.options.forEach((option, optionIndex) => {
    if (option.targetType !== "completion") return;
    const id = `terminal:${route.id}:${optionIndex}`;
    const position = positionFor(id, nodes.length);
    addNode({ id, entityId: id, kind: "terminal", label: "Completed", ...position, resourceIds: [], selectable: true, description: `Completed terminal reached from ${route.fromStageId}.` });
  }));
  model.resourcePools.forEach((resource, index) => {
    const position = positionFor(resource.id, nodes.length + index);
    addNode({ id: resource.id, entityId: resource.id, kind: "resource", label: resource.name ?? resource.id, ...position, resourceIds: [resource.id], selectable: true, description: `${resource.name ?? resource.id}, resource pool with capacity ${resource.capacity ?? "unavailable"}.` });
  });

  const byId = new Map(nodes.map((node) => [node.id, node]));
  model.sources.forEach((source) => {
    const from = byId.get(source.id); const to = byId.get(source.firstStageId);
    if (!to) { warnings.push(`Source ${source.id} references unknown stage ${source.firstStageId}.`); return; }
    if (!from) return;
    addEdge({ id: `entry:${source.id}:${source.firstStageId}`, routeId: `entry:${source.id}`, fromId: source.id, toId: source.firstStageId, routeType: "entry", probability: 1, label: "Entry", rework: false, path: edgePath(from, to, false), description: `${source.name ?? source.id} enters ${to.label}.` });
  });
  model.routes.forEach((route) => route.options.forEach((option, optionIndex) => {
    const from = byId.get(route.fromStageId);
    if (!from) { warnings.push(`Route ${route.id} references unknown origin stage ${route.fromStageId}.`); return; }
    const toId = option.targetType === "completion" ? `terminal:${route.id}:${optionIndex}` : option.targetId;
    const to = toId ? byId.get(toId) : undefined;
    if (!to) { warnings.push(`Route ${route.id} references unknown ${option.targetType} ${toId ?? "without an ID"}.`); return; }
    const rework = route.kind === "failure";
    const probability = typeof option.probability === "number" && Number.isFinite(option.probability) ? option.probability : null;
    const label = rework ? "Rework" : probability !== null ? `${Math.round(probability * 100)}%` : "Route";
    addEdge({ id: `route:${route.id}:${optionIndex}`, routeId: route.id, fromId: from.id, toId: to.id, routeType: rework ? "failure" : "success", probability, label, rework, path: edgePath(from, to, rework), description: `${from.label} routes to ${to.label}${rework ? " for rework" : ""}${probability !== null ? ` with ${Math.round(probability * 100)}% probability` : ""}.` });
  }));

  model.stages.forEach((stage) => {
    if (!stage.resourcePoolId) return;
    if (!byId.has(stage.resourcePoolId)) { warnings.push(`Stage ${stage.id} references unknown resource ${stage.resourcePoolId}.`); return; }
    addResourceLink({ id: `resource:${stage.resourcePoolId}:${stage.id}`, resourceId: stage.resourcePoolId, stageId: stage.id });
  });

  return { valid: warnings.length === 0, nodes: nodes.sort((a, b) => a.order - b.order), edges, resourceLinks, warnings };
}
