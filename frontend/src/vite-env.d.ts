/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_ROOT_LOGIN_URL?: string;
  readonly VITE_ENABLE_API_MOCKS?: string;
  readonly VITE_MOCK_SCENARIO?: string;
  readonly VITE_MOCK_DELAY_MS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
