import GroupsOutlinedIcon from '@mui/icons-material/GroupsOutlined';
import LocalLibraryOutlinedIcon from '@mui/icons-material/LocalLibraryOutlined';
import MonitorHeartOutlinedIcon from '@mui/icons-material/MonitorHeartOutlined';
import TerminalOutlinedIcon from '@mui/icons-material/TerminalOutlined';
import Box from '@mui/material/Box';
import { alpha, useTheme } from '@mui/material/styles';
import type { SvgIconComponent } from '@mui/icons-material';
import type { AgentKey } from './types';

type Look = {
  icon: SvgIconComponent;
  light: string;
  dark: string;
  placeholder: string;
  suggestions: string[];
};

/** How each agent looks and what it is good to ask, so they read as distinct at a glance. */
export const LOOKS: Record<AgentKey, Look> = {
  pair: {
    icon: TerminalOutlinedIcon,
    light: '#4f46e5',
    dark: '#8b8cf8',
    placeholder: 'Ask the PAIR Agent about config-service...',
    suggestions: ['What does FeatureFlag mean in this codebase?', 'Which work item task is next?', 'List the domain areas'],
  },
  doctor: {
    icon: MonitorHeartOutlinedIcon,
    light: '#e11d48',
    dark: '#fb7185',
    placeholder: 'Ask the Doctor to check something...',
    suggestions: ['Is config-service healthy?', 'Run the tests and diagnose any failure', 'Run lint and summarise the findings'],
  },
  librarian: {
    icon: LocalLibraryOutlinedIcon,
    light: '#b45309',
    dark: '#fbbf24',
    placeholder: 'Ask the Librarian, with sources...',
    suggestions: [
      'Why do duplicate names return 409 Conflict?',
      'Why are reads a scan-and-cache instead of indexed queries?',
      'Prepare context for changing key format validation',
    ],
  },
  team: {
    icon: GroupsOutlinedIcon,
    light: '#0f766e',
    dark: '#2dd4bf',
    placeholder: '',
    suggestions: [],
  },
};

export function useAccent(agent: AgentKey): string {
  const theme = useTheme();
  return theme.palette.mode === 'dark' ? LOOKS[agent].dark : LOOKS[agent].light;
}

export function AgentAvatar({ agent, size = 28 }: { agent: AgentKey; size?: number }) {
  const accent = useAccent(agent);
  const Icon = LOOKS[agent].icon;
  return (
    <Box
      aria-hidden
      sx={{
        width: size,
        height: size,
        flexShrink: 0,
        borderRadius: size >= 32 ? '10px' : '7px',
        display: 'grid',
        placeItems: 'center',
        color: accent,
        bgcolor: alpha(accent, 0.12),
        boxShadow: `inset 0 0 0 1px ${alpha(accent, 0.22)}`,
      }}
    >
      <Icon sx={{ fontSize: size * 0.58 }} />
    </Box>
  );
}
