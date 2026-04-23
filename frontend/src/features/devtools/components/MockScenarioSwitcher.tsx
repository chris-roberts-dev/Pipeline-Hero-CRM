import type { ChangeEvent } from 'react';

import { env } from '@/lib/config/env';
import {
  getMockScenario,
  mockScenarioOptions,
  setMockScenario,
  type MockScenarioKey,
} from '@/lib/dev/mockState';

export function MockScenarioSwitcher() {
  if (!env.enableApiMocks) {
    return null;
  }

  function handleChange(event: ChangeEvent<HTMLSelectElement>) {
    setMockScenario(event.target.value as MockScenarioKey);
    window.location.reload();
  }

  return (
    <label className="mock-switcher">
      <span>Mock</span>
      <select value={getMockScenario()} onChange={handleChange}>
        {mockScenarioOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
