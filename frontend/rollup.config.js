import resolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';
import terser from '@rollup/plugin-terser';

const isDev = process.env.BUILD === 'development';

// Use fixed filename for simplicity
const outputFile = 'abode-security-panel.js';

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
