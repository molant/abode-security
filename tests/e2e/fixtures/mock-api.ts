import axios from 'axios';

const MOCK_API_URL = process.env.MOCK_SERVER_URL || 'http://localhost:8000';

/**
 * Reset mock server to default state.
 *
 * Call before each test to ensure isolation.
 */
export async function resetMockServer() {
  try {
    await axios.post(`${MOCK_API_URL}/api/test/reset`, {}, { timeout: 2000 });
    console.log('Mock server state reset');
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('Failed to reset mock server:', errorMessage);
    throw new Error(
      `Mock server not responding at ${MOCK_API_URL}. ` +
      'Ensure docker-compose is running.'
    );
  }
}

/**
 * Set panel alarm mode via mock server.
 */
export async function setPanelMode(mode: 'standby' | 'home' | 'away') {
  const url = `${MOCK_API_URL}/api/v1/panel/mode/area_1/${mode}`;
  await axios.put(url);
  console.log(`Panel mode set to: ${mode}`);
}

/**
 * Get current mock server state (for debugging).
 */
export async function getMockServerState() {
  const response = await axios.get(`${MOCK_API_URL}/api/test/state`);
  return response.data;
}
