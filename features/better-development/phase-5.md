# Phase 5: Frontend Dev Workflow

**Status**: ✅ Complete (2025-01-16)

## Goal
Create frontend build infrastructure from scratch with TypeScript, Lit web components, Rollup bundling, cache busting, and hot reload development workflow.

## Context
From exploration, the current state:
- ✅ Compiled bundle exists: `custom_components/abode_security/www/abode-security-panel.js` (55KB)
- ❌ No source files: No TypeScript, no package.json, no build config
- ❌ No build tooling in repo

We're starting fresh with a simple sidebar panel that displays "Abode Configuration" text. This establishes the infrastructure for future feature development (which already exists in the compiled bundle but needs to be re-implemented).

## Prerequisites
- Node.js 20+ installed (check: `node --version`)
- npm installed (check: `npm --version`)
- Basic understanding of:
  - TypeScript
  - Lit web components
  - Rollup bundler
  - Home Assistant panel registration

## Steps

### 5.1 Create frontend directory structure

```bash
mkdir -p frontend/src
```

**Structure**:
```
frontend/
├── src/
│   ├── abode-panel.ts       # Main panel component
│   ├── types.ts             # TypeScript type definitions
│   └── styles.ts            # Shared style constants
├── package.json
├── package-lock.json
├── rollup.config.js
├── tsconfig.json
└── .nvmrc
```

### 5.2 Create package.json

**File**: `frontend/package.json`

```json
{
  "name": "abode-security-frontend",
  "version": "1.0.0",
  "description": "Frontend panel for Abode Security Home Assistant integration",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "rollup -c",
    "watch": "rollup -c -w",
    "dev": "rollup -c -w --environment BUILD:development"
  },
  "keywords": ["home-assistant", "abode", "security"],
  "author": "",
  "license": "MIT",
  "dependencies": {
    "lit": "^3.2.0"
  },
  "devDependencies": {
    "@rollup/plugin-node-resolve": "^15.2.3",
    "@rollup/plugin-terser": "^0.4.4",
    "@rollup/plugin-typescript": "^11.1.6",
    "rollup": "^4.22.0",
    "tslib": "^2.7.0",
    "typescript": "^5.6.2"
  }
}
```

**Install dependencies**:
```bash
cd frontend
npm install
cd ..
```

### 5.3 Create rollup.config.js with cache busting

**File**: `frontend/rollup.config.js`

```javascript
import resolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';
import terser from '@rollup/plugin-terser';

const isDev = process.env.BUILD === 'development';

// Generate timestamp for cache busting in production
const timestamp = new Date().getTime();

// In development: use fixed name for easier debugging
// In production: append timestamp to bust cache
const outputFile = isDev
  ? 'abode-security-panel.js'
  : `abode-security-panel.${timestamp}.js`;

export default {
  input: 'src/abode-panel.ts',
  output: {
    file: `../custom_components/abode_security/www/${outputFile}`,
    format: 'es',
    sourcemap: isDev,
  },
  plugins: [
    resolve(),
    typescript({
      sourceMap: isDev,
      inlineSources: isDev,
    }),
    !isDev && terser({
      format: {
        comments: false,
      },
    }),
  ],
};
```

**Cache busting strategy**:
- Development: `abode-security-panel.js` (fixed name, easy to reference)
- Production: `abode-security-panel.1703001234567.js` (timestamp for cache invalidation)

**Note**: For production cache busting to work fully, you'll need to update the panel registration in `__init__.py` to use the timestamped filename. Consider creating a manifest file or using HA's resource versioning.

**For now**, we'll use the fixed filename in both modes for simplicity. Remove the timestamp logic:

```javascript
const outputFile = 'abode-security-panel.js';
```

We can add proper cache busting later when needed.

### 5.4 Create tsconfig.json

**File**: `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "experimentalDecorators": true,
    "useDefineForClassFields": false
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "../custom_components"]
}
```

### 5.5 Create .nvmrc

**File**: `frontend/.nvmrc`

```
20
```

This ensures everyone uses Node 20 (LTS).

### 5.6 Create initial panel component

**File**: `frontend/src/abode-panel.ts`

```typescript
import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('abode-configuration-panel')
export class AbodeConfigurationPanel extends LitElement {
  static styles = css`
    :host {
      display: block;
      padding: 16px;
      background-color: var(--primary-background-color);
      color: var(--primary-text-color);
      min-height: 100vh;
    }

    .panel-content {
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      font-size: 24px;
      font-weight: 400;
      margin: 0 0 16px 0;
      color: var(--primary-text-color);
    }
  `;

  render() {
    return html`
      <div class="panel-content">
        <h1>Abode Configuration</h1>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'abode-configuration-panel': AbodeConfigurationPanel;
  }
}
```

**Why these styles**:
- Uses HA CSS variables (`--primary-background-color`, etc.) for theming
- Responsive max-width
- Proper spacing
- Dark mode support via HA variables

### 5.7 Create types file (for future use)

**File**: `frontend/src/types.ts`

```typescript
/**
 * Type definitions for Abode Security frontend.
 */

export interface AbodePanel {
  mode: {
    area_1: 'standby' | 'home' | 'away';
    area_1_label: string;
  };
  online: string;
  battery: string;
}

export interface AbodeDevice {
  id: string;
  name: string;
  type: string;
  type_tag: string;
  status: string;
}

// Add more types as needed when expanding functionality
```

### 5.8 Build the frontend

**First build**:
```bash
cd frontend
npm run build
```

**Expected output**:
```
frontend/src/abode-panel.ts → ../custom_components/abode_security/www/abode-security-panel.js...
created ../custom_components/abode_security/www/abode-security-panel.js in 1.2s
```

**Verify file created**:
```bash
ls -lh custom_components/abode_security/www/
```

Should show `abode-security-panel.js`.

### 5.9 Register panel in Home Assistant

**File**: `custom_components/abode_security/__init__.py`

Find `async_setup_entry` function (around line 95). Add panel registration after the integration is set up successfully.

Add this code near the end of `async_setup_entry`, before the `return True`:

```python
# Register frontend panel for configuration
panel_url = "/abode_security_panel"
panel_name = "abode_security_panel"

# Register static path for panel JavaScript
await hass.http.async_register_static_paths([
    {
        "url_path": panel_url,
        "path": hass.config.path(
            "custom_components/abode_security/www"
        ),
        "cache_headers": False,  # Disable caching during development
    }
])

# Register the panel in sidebar
await hass.async_add_executor_job(
    hass.components.frontend.async_register_built_in_panel,
    "iframe",  # Use iframe panel type
    "Abode",  # Display name in sidebar
    "mdi:shield-home",  # Icon
    panel_name,  # Unique identifier
    {"url": f"{panel_url}/abode-security-panel.js"},  # Config
    require_admin=False,
)
```

**Note**: The exact registration method may vary based on HA version. If this doesn't work, check:
- HA documentation for custom panels
- Other integrations that register panels (e.g., HACS)
- HA core source code: `homeassistant/components/frontend/__init__.py`

**Alternative approach** (if iframe doesn't work):

Create a custom panel configuration file:

**File**: `custom_components/abode_security/www/abode-panel-config.js`
```javascript
export default {
  type: 'module',
  name: 'abode-configuration-panel',
  embed_iframe: false,
  trust_external_script: false,
  js_url: '/abode_security_panel/abode-security-panel.js',
};
```

Then register with:
```python
await hass.components.frontend.async_register_built_in_panel(
    "custom",
    "Abode",
    "mdi:shield-home",
    "abode_security",
    {"_panel_custom": {
        "name": "abode-configuration-panel",
        "js_url": "/abode_security_panel/abode-security-panel.js",
        "module_url": "/abode_security_panel/abode-security-panel.js",
    }},
)
```

### 5.10 Test in Home Assistant

**Restart HA**:
```bash
docker-compose restart homeassistant
```

**Or reload integration** (if supported):
- Settings → Devices & Services → Abode Security → ⋮ → Reload

**Check sidebar**:
1. Go to http://localhost:8123
2. Look for "Abode" in the sidebar (should have shield-home icon)
3. Click it
4. Should see "Abode Configuration" heading

**Debug if not appearing**:

1. **Check HA logs**:
```bash
docker logs abode-dev-ha | grep -i abode
```

2. **Check file exists**:
```bash
docker exec abode-dev-ha ls -la /config/custom_components/abode_security/www/
```

3. **Check browser console**:
- F12 → Console tab
- Look for JavaScript errors

4. **Check panel registration**:
```bash
docker exec abode-dev-ha ha core state | grep panel
```

### 5.11 Setup development workflow (watch mode)

**Terminal 1** - Start HA:
```bash
./scripts/dev.sh
```

**Terminal 2** - Watch frontend:
```bash
cd frontend
npm run watch
```

**Now test hot reload**:

1. **Edit** `frontend/src/abode-panel.ts`:
   ```typescript
   <h1>Abode Configuration Panel</h1>  // Changed text
   ```

2. **Save** - Rollup automatically rebuilds

3. **Refresh** browser (Ctrl+Shift+R or Cmd+Shift+R)

4. **See changes** - heading should update

**Note**: Full hot module reload (no page refresh) requires additional setup with webpack or vite. For now, auto-rebuild + manual refresh is sufficient.

### 5.12 Add .gitignore entries

**File**: `frontend/.gitignore`

```
node_modules/
dist/
*.log
.DS_Store
```

**Add to root .gitignore**:
```
# Frontend build
frontend/node_modules/
frontend/dist/
frontend/*.log
```

**Keep in git**:
- `frontend/src/` - Source files
- `frontend/package.json` - Dependencies
- `frontend/package-lock.json` - Lock file
- `frontend/rollup.config.js` - Build config
- `frontend/tsconfig.json` - TS config
- `custom_components/abode_security/www/abode-security-panel.js` - Built file

## Success Criteria
- ✅ `frontend/` directory structure created
- ✅ `npm run build` successfully creates `custom_components/abode_security/www/abode-security-panel.js`
- ✅ "Abode" panel appears in HA sidebar
- ✅ Clicking panel shows "Abode Configuration" heading
- ✅ `npm run watch` auto-rebuilds on file changes
- ✅ Browser refresh shows updated changes
- ✅ No console errors in browser

## Troubleshooting

**Panel not appearing in sidebar**:
- Check `__init__.py` panel registration code
- Restart HA: `docker-compose restart homeassistant`
- Check HA logs for registration errors

**Build errors**:
- Verify Node version: `node --version` (should be 20+)
- Delete node_modules and reinstall: `rm -rf node_modules package-lock.json && npm install`
- Check for TypeScript errors: `npx tsc --noEmit`

**Changes not reflecting**:
- Hard refresh: Ctrl+Shift+R
- Clear browser cache
- Check Rollup is watching: should show "waiting for changes..."
- Verify file timestamp changed: `ls -l custom_components/abode_security/www/`

**HA can't load JavaScript**:
- Check static path registration in `__init__.py`
- Verify file permissions: `ls -la custom_components/abode_security/www/`
- Check HA http configuration

## Commit Message
```
feat: Add frontend build infrastructure

- Create frontend/src/ with TypeScript source structure
- Add package.json with build/watch/dev scripts
- Implement Rollup bundling with Terser minification
- Create initial Lit panel component showing "Abode Configuration"
- Register panel in Home Assistant sidebar
- Output to custom_components/abode_security/www/
- Support hot reload development workflow

Phase 5/8 of better-development feature
```

## Next Steps
After completing this phase:
- Move to [Phase 6: Playwright Testing Setup](phase-6.md)
- Set up E2E testing to verify panel appears and displays correctly
