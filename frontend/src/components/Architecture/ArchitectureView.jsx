import React, { useState, useEffect, useCallback } from 'react';
import { NODES, CELERY_TASKS } from './architectureData';
import { ArchitectureMap } from './ArchitectureMap';
import { ArchitectureInspector } from './ArchitectureInspector';

export const ArchitectureView = ({ onBack }) => {
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [isolatedNodes, setIsolatedNodes] = useState(null);

  useEffect(() => {
    const originalTitle = document.title;
    document.title = 'FlashMarket — Системная Архитектура';
    window.scrollTo({ top: 0, behavior: 'smooth' });
    return () => {
      document.title = originalTitle;
    };
  }, []);

  // Compute connected nodes for a selected service
  const getServiceConnectedNodes = useCallback((nodeId) => {
    const sNodeId = nodeId.startsWith('node-') ? nodeId : `node-${nodeId}`;
    const connected = new Set([sNodeId]);

    const entity = NODES.find((n) => n.id === sNodeId || n.entityId === nodeId);

    // Infrastructure and inter-service connections
    if (entity?.type === 'service') {
      // 1. Direct infrastructure connections
      if ((entity.publishes && entity.publishes.length > 0) || (entity.consumes && entity.consumes.length > 0)) {
        connected.add('node-component-rabbitmq');
      }
      connected.add('node-component-postgres');
      if (['service-inventory', 'service-auth', 'service-catalog'].includes(entity.entityId)) {
        connected.add('node-component-redis');
      }
      if (entity.entityId === 'service-media') {
        connected.add('node-component-s3');
      }

      // 2. Inter-service event connections (producers & consumers)
      const myPublishes = new Set(entity.publishes || []);
      const myConsumes = new Set(entity.consumes || []);

      NODES.filter((n) => n.type === 'service' && n.id !== sNodeId).forEach((other) => {
        const consumesMine = (other.consumes || []).some((e) => myPublishes.has(e));
        const producesMine = (other.publishes || []).some((e) => myConsumes.has(e));
        if (consumesMine || producesMine) {
          connected.add(other.id);
        }
      });

      // 3. Inter-service HTTP calls & background tasks
      if (entity.entityId === 'service-inventory') {
        connected.add('node-service-drops');
        connected.add('node-component-celery');
      } else if (entity.entityId === 'service-drops') {
        connected.add('node-service-inventory');
        connected.add('node-component-celery');
      } else if (entity.entityId === 'service-media') {
        connected.add('node-component-celery');
      } else if (entity.entityId === 'service-auth') {
        connected.add('node-component-celery');
      }
    } else if (entity?.type === 'infra') {
      // If an infra node is selected, add connected services
      NODES.filter((n) => n.type === 'service').forEach((s) => {
        if (entity.entityId === 'component-rabbitmq' && ((s.publishes && s.publishes.length > 0) || (s.consumes && s.consumes.length > 0))) {
          connected.add(s.id);
        } else if (entity.entityId === 'component-postgres') {
          connected.add(s.id);
        } else if (entity.entityId === 'component-redis' && ['service-inventory', 'service-auth', 'service-catalog'].includes(s.entityId)) {
          connected.add(s.id);
        } else if (entity.entityId === 'component-s3' && s.entityId === 'service-media') {
          connected.add(s.id);
        }
      });
    }

    // Celery tasks
    if (nodeId === 'component-celery' || sNodeId === 'node-component-celery') {
      CELERY_TASKS.forEach((t) => {
        t.nodes.forEach((n) => connected.add(n));
      });
    }

    return Array.from(connected);
  }, []);

  // Select a node (null = deselect)
  const handleSelectNode = (nodeId) => {
    if (nodeId === null || nodeId === selectedNodeId) {
      // Deselect
      setSelectedNodeId(null);
      setIsolatedNodes(null);
      return;
    }
    setSelectedNodeId(nodeId);
    const connected = getServiceConnectedNodes(nodeId);
    setIsolatedNodes(connected);
  };

  // Close inspector
  const handleCloseInspector = () => {
    setSelectedNodeId(null);
    setIsolatedNodes(null);
  };

  // Isolate a specific route or event
  const handleIsolateRoute = ({ nodes }) => {
    setIsolatedNodes(nodes);
  };

  // Reset to service-level isolation
  const handleResetServiceIsolation = () => {
    if (selectedNodeId) {
      const connected = getServiceConnectedNodes(selectedNodeId);
      setIsolatedNodes(connected);
    }
  };

  return (
    <div
      className="w-full bg-[#F8F9FA] flex flex-col flex-1 relative overflow-hidden"
      style={{ minHeight: 'calc(100dvh - 65px)' }}
    >
      {/* Main Architecture Interactive Canvas */}
      <div
        className="relative flex-1 w-full flex flex-col overflow-hidden"
        style={{
          height: 'calc(100dvh - 65px)',
          minHeight: '400px',
        }}
      >
        <ArchitectureMap
          selectedNodeId={selectedNodeId}
          onSelectNode={handleSelectNode}
          isolatedNodes={isolatedNodes}
          activeCategoryFilter="overview"
        />

        {/* Inspector Drawer / Bottom Sheet */}
        {selectedNodeId && (
          <ArchitectureInspector
            nodeId={selectedNodeId}
            onClose={handleCloseInspector}
            onIsolateRoute={handleIsolateRoute}
            onResetServiceIsolation={handleResetServiceIsolation}
          />
        )}
      </div>
    </div>
  );
};

export default ArchitectureView;
