import '@fontsource-variable/inter';
import '@fontsource-variable/jetbrains-mono';
import { alpha, createTheme } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface TypeBackground {
    sidebar: string;
    raised: string;
    bubble: string;
    code: string;
    hover: string;
  }
  interface Palette {
    border: string;
    borderStrong: string;
  }
  interface PaletteOptions {
    border?: string;
    borderStrong?: string;
  }
}

export type Mode = 'light' | 'dark';
export type ModePreference = Mode | 'system';

export const SANS = '"Inter Variable", Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
export const MONO = '"JetBrains Mono Variable", ui-monospace, "Cascadia Code", "SF Mono", Consolas, monospace';

const tokens = {
  light: {
    bg: '#fafaf9',
    sidebar: '#f4f4f2',
    paper: '#ffffff',
    raised: '#ffffff',
    bubble: '#f0efec',
    code: '#f6f6f4',
    hover: 'rgba(24, 24, 27, 0.045)',
    text: '#18181b',
    secondary: '#5f5f69',
    disabled: '#a1a1aa',
    border: 'rgba(24, 24, 27, 0.09)',
    borderStrong: 'rgba(24, 24, 27, 0.16)',
    primary: '#4f46e5',
    success: '#15803d',
    warning: '#b45309',
    error: '#dc2626',
    info: '#2563eb',
  },
  dark: {
    bg: '#131315',
    sidebar: '#0e0e10',
    paper: '#1a1a1d',
    raised: '#202024',
    bubble: '#26262b',
    code: '#0f0f11',
    hover: 'rgba(255, 255, 255, 0.055)',
    text: '#ededf0',
    secondary: '#a1a1aa',
    disabled: '#5f5f69',
    border: 'rgba(255, 255, 255, 0.08)',
    borderStrong: 'rgba(255, 255, 255, 0.15)',
    primary: '#8b8cf8',
    success: '#4ade80',
    warning: '#fbbf24',
    error: '#f87171',
    info: '#60a5fa',
  },
};

export function makeTheme(mode: Mode) {
  const t = tokens[mode];
  const dark = mode === 'dark';
  return createTheme({
    palette: {
      mode,
      primary: { main: t.primary, contrastText: dark ? '#0e0e10' : '#ffffff' },
      success: { main: t.success },
      warning: { main: t.warning },
      error: { main: t.error },
      info: { main: t.info },
      text: { primary: t.text, secondary: t.secondary, disabled: t.disabled },
      background: {
        default: t.bg,
        paper: t.paper,
        sidebar: t.sidebar,
        raised: t.raised,
        bubble: t.bubble,
        code: t.code,
        hover: t.hover,
      },
      divider: t.border,
      border: t.border,
      borderStrong: t.borderStrong,
      action: { hover: t.hover, selected: dark ? 'rgba(255,255,255,0.08)' : 'rgba(24,24,27,0.07)' },
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: SANS,
      fontSize: 14,
      h1: { fontWeight: 650, letterSpacing: '-0.025em' },
      h2: { fontWeight: 650, letterSpacing: '-0.02em' },
      h3: { fontWeight: 650, letterSpacing: '-0.02em' },
      h4: { fontWeight: 650, letterSpacing: '-0.02em' },
      h5: { fontWeight: 650, letterSpacing: '-0.015em' },
      h6: { fontWeight: 600, letterSpacing: '-0.01em' },
      subtitle1: { fontWeight: 600 },
      subtitle2: { fontWeight: 600, fontSize: '0.8125rem' },
      body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
      body2: { fontSize: '0.8125rem', lineHeight: 1.55 },
      caption: { fontSize: '0.75rem', lineHeight: 1.45 },
      overline: { fontWeight: 600, fontSize: '0.6875rem', letterSpacing: '0.06em', lineHeight: 1.6 },
      button: { textTransform: 'none', fontWeight: 550, letterSpacing: 0 },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            fontFeatureSettings: '"cv11", "ss01", "ss03"',
            WebkitFontSmoothing: 'antialiased',
            MozOsxFontSmoothing: 'grayscale',
          },
          '::selection': { background: alpha(t.primary, 0.25) },
          '*::-webkit-scrollbar': { width: 10, height: 10 },
          '*::-webkit-scrollbar-thumb': {
            backgroundColor: t.borderStrong,
            borderRadius: 8,
            border: '3px solid transparent',
            backgroundClip: 'content-box',
          },
          '*::-webkit-scrollbar-track': { background: 'transparent' },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 9, paddingInline: 14, minHeight: 34 },
          sizeSmall: { minHeight: 30, paddingInline: 10, fontSize: '0.8125rem' },
          outlined: { borderColor: t.borderStrong, '&:hover': { borderColor: t.borderStrong, backgroundColor: t.hover } },
          contained: { '&:hover': { filter: 'brightness(1.08)' } },
        },
      },
      MuiIconButton: {
        styleOverrides: { root: { borderRadius: 9, '&:hover': { backgroundColor: t.hover } } },
      },
      MuiTooltip: {
        defaultProps: { arrow: false, enterDelay: 350 },
        styleOverrides: {
          tooltip: {
            backgroundColor: dark ? '#ededf0' : '#18181b',
            color: dark ? '#18181b' : '#fafaf9',
            fontSize: '0.75rem',
            fontWeight: 500,
            borderRadius: 7,
            padding: '5px 9px',
          },
        },
      },
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiDialog: {
        defaultProps: { fullWidth: true },
        styleOverrides: {
          paper: {
            borderRadius: 16,
            border: `1px solid ${t.border}`,
            backgroundColor: t.raised,
            boxShadow: dark ? '0 24px 64px rgba(0,0,0,0.6)' : '0 24px 64px rgba(24,24,27,0.16)',
          },
        },
      },
      MuiBackdrop: {
        styleOverrides: { root: { backgroundColor: dark ? 'rgba(0,0,0,0.6)' : 'rgba(24,24,27,0.3)', backdropFilter: 'blur(2px)' } },
      },
      MuiMenu: {
        styleOverrides: {
          paper: {
            borderRadius: 12,
            border: `1px solid ${t.border}`,
            backgroundColor: t.raised,
            boxShadow: dark ? '0 12px 32px rgba(0,0,0,0.5)' : '0 12px 32px rgba(24,24,27,0.12)',
            marginTop: 4,
          },
          list: { padding: 4 },
        },
      },
      MuiMenuItem: {
        styleOverrides: {
          root: { borderRadius: 8, fontSize: '0.8125rem', minHeight: 34, paddingInline: 10 },
        },
      },
      MuiListItemIcon: { styleOverrides: { root: { minWidth: 30 } } },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: 7, fontWeight: 550, fontSize: '0.75rem' },
          sizeSmall: { height: 22 },
          outlined: { borderColor: t.borderStrong },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 10,
            backgroundColor: t.paper,
            '& .MuiOutlinedInput-notchedOutline': { borderColor: t.borderStrong },
          },
        },
      },
      MuiAlert: {
        styleOverrides: { root: { borderRadius: 12, fontSize: '0.8125rem' } },
      },
      MuiSwitch: {
        styleOverrides: { root: { marginRight: 4 } },
      },
      MuiSnackbarContent: {
        styleOverrides: { root: { borderRadius: 10 } },
      },
    },
  });
}
