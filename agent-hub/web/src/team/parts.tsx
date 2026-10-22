import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import { alpha, useTheme } from '@mui/material/styles';
import type { ReactNode } from 'react';
import { MONO } from '../theme';
import type { RunState, RunSummary } from '../types';

type Tone = 'success' | 'error' | 'warning' | 'info' | 'neutral';

export function useTone(tone: Tone): string {
  const theme = useTheme();
  return tone === 'neutral' ? theme.palette.text.secondary : theme.palette[tone].main;
}

export function StatusChip({ label, tone }: { label: string; tone: Tone }) {
  const colour = useTone(tone);
  return (
    <Chip
      size="small"
      label={label.charAt(0).toUpperCase() + label.slice(1)}
      sx={{ bgcolor: alpha(colour, 0.12), color: colour, border: `1px solid ${alpha(colour, 0.25)}` }}
    />
  );
}

const STATE_LABELS: Record<RunState, [string, Tone]> = {
  running: ['Running', 'info'],
  awaiting_approval: ['Needs approval', 'warning'],
  approved: ['Approved', 'info'],
  rejected: ['Rejected', 'neutral'],
  finished: ['Finished', 'neutral'],
  interrupted: ['Interrupted', 'neutral'],
};

export function outcomeTone(outcome?: string): Tone {
  if (outcome === 'verified' || outcome === 'healthy') return 'success';
  if (outcome === 'blocked' || outcome === 'inconclusive') return 'warning';
  return 'error';
}

export function RunChip({ run }: { run: RunSummary }) {
  if (run.state === 'finished') return <StatusChip label={(run.outcome ?? 'finished').replace(/_/g, ' ')} tone={outcomeTone(run.outcome)} />;
  const [label, tone] = STATE_LABELS[run.state];
  return <StatusChip label={label} tone={tone} />;
}

export function Card({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <Box component="section" sx={{ border: 1, borderColor: 'border', borderRadius: 3, bgcolor: 'background.paper', overflow: 'hidden' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1.25, borderBottom: 1, borderColor: 'border' }}>
        <Typography variant="subtitle2" sx={{ flex: 1 }}>
          {title}
        </Typography>
        {aside}
      </Box>
      <Box sx={{ p: 2, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 1.75 }}>{children}</Box>
    </Box>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box>
      <Typography variant="overline" color="text.secondary" component="div">
        {label}
      </Typography>
      <Box sx={{ fontSize: '0.875rem', lineHeight: 1.6, overflowWrap: 'anywhere' }}>{children}</Box>
    </Box>
  );
}

export function Paths({ paths }: { paths: string[] }) {
  if (!paths.length) return <Typography variant="body2" color="text.disabled">None</Typography>;
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
      {paths.map((path) => (
        <Box key={path} component="code" sx={{ fontFamily: MONO, fontSize: '0.75rem', px: 0.75, py: 0.25, borderRadius: 1.25, bgcolor: 'background.code', border: 1, borderColor: 'border', wordBreak: 'break-all' }}>
          {path}
        </Box>
      ))}
    </Box>
  );
}

export function Bullets({ items, mono }: { items: string[]; mono?: boolean }) {
  if (!items.length) return <Typography variant="body2" color="text.disabled">None</Typography>;
  return (
    <Box component="ul" sx={{ m: 0, pl: 2.25, overflowWrap: 'anywhere', '& li': { my: 0.4 }, ...(mono && { fontFamily: MONO, fontSize: '0.78rem' }) }}>
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </Box>
  );
}

export function Mono({ children }: { children: ReactNode }) {
  return (
    <Box component="pre" sx={{ m: 0, p: 1.25, fontFamily: MONO, fontSize: '0.75rem', lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word', bgcolor: 'background.code', border: 1, borderColor: 'border', borderRadius: 2, maxHeight: 260, overflow: 'auto' }}>
      {children}
    </Box>
  );
}

export function PassIcon({ passed }: { passed: boolean }) {
  return passed ? <CheckRoundedIcon sx={{ fontSize: 16, color: 'success.main' }} /> : <CloseRoundedIcon sx={{ fontSize: 16, color: 'error.main' }} />;
}

/** A unified diff with additions, deletions and hunk headers coloured. */
export function DiffView({ diff }: { diff: string }) {
  const theme = useTheme();
  const { success, error, info } = theme.palette;
  return (
    <Box sx={{ border: 1, borderColor: 'border', borderRadius: 2, overflow: 'auto', bgcolor: 'background.code', maxHeight: 520 }}>
      <Box component="pre" sx={{ m: 0, py: 1, fontFamily: MONO, fontSize: '0.75rem', lineHeight: 1.6, minWidth: 'fit-content' }}>
        {diff.split('\n').map((line, index) => {
          const file = line.startsWith('diff --git');
          const style = file
            ? { color: 'text.primary', fontWeight: 700, bgcolor: 'background.hover', mt: index ? 1 : 0 }
            : line.startsWith('@@')
              ? { color: info.main }
              : line.startsWith('+') && !line.startsWith('+++')
                ? { color: success.main, bgcolor: alpha(success.main, 0.1) }
                : line.startsWith('-') && !line.startsWith('---')
                  ? { color: error.main, bgcolor: alpha(error.main, 0.1) }
                  : { color: 'text.secondary' };
          return (
            <Box key={index} sx={{ px: 1.75, whiteSpace: 'pre', ...style }}>
              {line || ' '}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
