import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface WSMessage {
  type: 'progress' | 'status' | 'new_task';
  task_id: number;
  progress?: number;
  status?: string;
}

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/progress`);

    ws.onmessage = (event) => {
      const data: WSMessage = JSON.parse(event.data);

      if (data.type === 'progress' || data.type === 'status') {
        // Update task in cache
        queryClient.setQueriesData({ queryKey: ['tasks'] }, (old) => {
          if (!Array.isArray(old)) return old;
          return old.map((task) => {
            if (task.id === data.task_id) {
              return {
                ...task,
                progress: data.progress ?? task.progress,
                status: data.status ?? task.status,
              };
            }
            return task;
          });
        });

        // Update stats
        if (data.type === 'status') {
          queryClient.invalidateQueries({ queryKey: ['taskStats'] });
        }
      }

      if (data.type === 'new_task') {
        // Refetch tasks list
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        queryClient.invalidateQueries({ queryKey: ['taskStats'] });
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    // Keep alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);

    ws.onclose = () => {
      clearInterval(pingInterval);
      setTimeout(connect, 3000);
    };

    wsRef.current = ws;
  }, [queryClient]);

  useEffect(() => {
    connect();

    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return wsRef.current;
}
