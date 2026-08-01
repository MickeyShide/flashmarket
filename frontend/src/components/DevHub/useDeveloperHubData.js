import { useEffect, useState } from 'react';
import { loadDeveloperHubData, loadServiceStatuses } from './openapi';

export function useDeveloperHubData() {
  const [state, setState] = useState({ loading: true, data: null, error: null, statuses: {} });

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const data = await loadDeveloperHubData(controller.signal);
        setState({ loading: false, data, error: null, statuses: {} });
        const statuses = await loadServiceStatuses(data.metadata.services, controller.signal);
        if (!controller.signal.aborted) {
          setState((current) => ({ ...current, statuses }));
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setState({ loading: false, data: null, error: error.message, statuses: {} });
        }
      }
    }
    load();
    return () => controller.abort();
  }, []);

  return state;
}
