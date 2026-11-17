/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // ---- v2「精密星图」语义色（全部映射 CSS 变量） ----
        bg: 'var(--bg)',
        panel: {
          DEFAULT: 'var(--panel)',
          2: 'var(--panel-2)',
        },
        line: {
          DEFAULT: 'var(--line)',
          strong: 'var(--line-strong)',
        },
        ink: 'var(--text)',
        t2: 'var(--t2)',
        t3: 'var(--t3)',
        gold: {
          DEFAULT: 'var(--gold)',
          deep: 'var(--gold-deep)',
          ink: 'var(--gold-ink)',
          soft: 'var(--gold-soft)',
        },
        danger: {
          DEFAULT: 'var(--danger)',
          soft: 'var(--danger-soft)',
        },
        success: {
          DEFAULT: 'var(--success)',
          soft: 'var(--success-soft)',
        },
        steel: 'var(--steel)',
        sage: 'var(--sage)',

        // ---- 旧页面兼容（P6 删除） ----
        primary: {
          DEFAULT: 'var(--primary-color)',
          dark: 'var(--primary-hover)',
        },
        accent: {
          blue: 'var(--accent-blue)',
          green: 'var(--accent-green)',
          red: 'var(--accent-red)',
          purple: 'var(--accent-purple)',
        },
        dark: {
          bg: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
          elevated: 'var(--bg-elevated)',
        },
        light: {
          bg: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
        },
      },
      fontFamily: {
        display: ['var(--font-display)'],
        body: ['var(--font-body)'],
        mono: ['var(--font-mono)'],
        sans: ['var(--font-body)'],
      },
      borderRadius: {
        sm: 'var(--r-sm)',
        md: 'var(--r-md)',
        lg: 'var(--r-lg)',
      },
      // 不覆盖 Tailwind 默认数字间距（旧页面在用 p-6/p-8 等），
      // 仅补充具名布局尺寸；新组件按 4px 基准取默认刻度即可。
      spacing: {
        rail: 'var(--rail-w)',
        topbar: 'var(--topbar-h)',
      },
      transitionTimingFunction: {
        out: 'var(--ease-out)',
      },
      transitionDuration: {
        fast: 'var(--d-fast)',
        base: 'var(--d-base)',
        panel: 'var(--d-panel)',
        enter: 'var(--d-enter)',
      },
      boxShadow: {
        float: 'var(--shadow-float)',
      },
      maxWidth: {
        shell: 'var(--max-w)',
        read: 'var(--read-col)',
      },
    },
  },
  plugins: [],
}
