import AutoStoriesOutlinedIcon from '@mui/icons-material/AutoStoriesOutlined';
import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import HandymanOutlinedIcon from '@mui/icons-material/HandymanOutlined';
import Box from '@mui/material/Box';
import ButtonBase from '@mui/material/ButtonBase';
import CircularProgress from '@mui/material/CircularProgress';
import Collapse from '@mui/material/Collapse';
import Typography from '@mui/material/Typography';
import { useState } from 'react';
import { argumentSummary, skillOf, toolLabel } from '../format';
import { MONO } from '../theme';
import type { ToolView } from '../types';

function StatusIcon({ status }: { status: ToolView['status'] }) {
  if (status === 'running') return <CircularProgress size={13} thickness={5} sx={{ color: 'text.secondary' }} />;
  if (status === 'error') return <CloseRoundedIcon sx={{ fontSize: 16, color: 'error.main' }} />;
  return <CheckRoundedIcon sx={{ fontSize: 16, color: 'success.main' }} />;
}

function Pane({ label, text, error }: { label: string; text: string; error?: boolean }) {
  return (
    <Box>
      <Typography variant="overline" color="text.secondary">
        {label}
      </Typography>
      <Box
        component="pre"
        sx={{
          m: 0,
          p: 1.25,
          maxHeight: 340,
          overflow: 'auto',
          fontFamily: MONO,
          fontSize: '0.75rem',
          lineHeight: 1.55,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          bgcolor: 'background.code',
          border: 1,
          borderColor: 'border',
          borderRadius: 2,
          color: error ? 'error.main' : 'text.primary',
        }}
      >
        {text || '(empty)'}
      </Box>
    </Box>
  );
}

const ANSI = /\u001b\[[0-9;]*[A-Za-z]/g;

/** A JSON object result (a test run's command, exit code, stdout...) as labelled fields,
 * strings shown as the text they hold rather than escaped. */
function Result({ text, error }: { text: string; error: boolean }) {
  let fields: [string, unknown][] | null = null;
  try {
    const parsed: unknown = JSON.parse(text);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) fields = Object.entries(parsed);
  } catch {
    // Plain text: shown as it is.
  }
  if (!fields) return <Pane label={error ? 'Error' : 'Result'} text={text.replace(ANSI, '')} error={error} />;
  return (
    <Box sx={{ display: 'grid', gap: 1 }}>
      <Typography variant="overline" color="text.secondary" sx={{ mb: -1 }}>
        {error ? 'Error' : 'Result'}
      </Typography>
      <Box sx={{ border: 1, borderColor: 'border', borderRadius: 2, bgcolor: 'background.code', overflow: 'hidden' }}>
        {fields.map(([key, value]) => {
          const shown = typeof value === 'string' ? value.replace(ANSI, '').trim() : JSON.stringify(value, null, 2);
          const long = shown.includes('\n') || shown.length > 80;
          return (
            <Box key={key} sx={{ display: long ? 'block' : 'flex', gap: 1.5, px: 1.25, py: 0.75, '& + &': { borderTop: 1, borderColor: 'border' } }}>
              <Typography sx={{ fontFamily: MONO, fontSize: '0.72rem', color: 'text.secondary', minWidth: 96, flexShrink: 0 }}>{key}</Typography>
              <Box
                component="pre"
                sx={{ m: 0, mt: long ? 0.5 : 0, fontFamily: MONO, fontSize: '0.75rem', lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 280, overflow: 'auto', color: key === 'error' && value ? 'error.main' : 'text.primary' }}
              >
                {shown || '(empty)'}
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

function ToolRow({ tool }: { tool: ToolView }) {
  const [open, setOpen] = useState(false);
  const skill = skillOf(tool);
  const { tool: name, source } = toolLabel(tool.name);
  return (
    <Box sx={{ '& + &': { borderTop: 1, borderColor: 'border' } }}>
      <ButtonBase
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        sx={{
          width: '100%',
          justifyContent: 'flex-start',
          gap: 1.25,
          px: 1.5,
          py: 0.9,
          textAlign: 'left',
          '&:hover': { bgcolor: 'background.hover' },
        }}
      >
        <Box sx={{ width: 16, display: 'grid', placeItems: 'center', flexShrink: 0 }}>
          <StatusIcon status={tool.status} />
        </Box>
        <Box sx={{ minWidth: 0, flex: 1, display: 'flex', alignItems: 'baseline', gap: 1 }}>
          {skill ? (
            <Typography sx={{ fontSize: '0.8125rem', fontWeight: 550, flexShrink: 0, display: 'flex', alignItems: 'center', gap: 0.75 }}>
              <AutoStoriesOutlinedIcon sx={{ fontSize: 14, color: 'text.secondary', alignSelf: 'center' }} />
              Loaded skill <Box component="span" sx={{ fontFamily: MONO, fontSize: '0.78rem' }}>{skill}</Box>
            </Typography>
          ) : (
            <>
              <Typography sx={{ fontFamily: MONO, fontSize: '0.78rem', fontWeight: 600, flexShrink: 0 }}>{name}</Typography>
              <Typography noWrap color="text.secondary" sx={{ fontSize: '0.8125rem', minWidth: 0 }}>
                {argumentSummary(tool.arguments)}
              </Typography>
            </>
          )}
        </Box>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ flexShrink: 0, display: { xs: 'none', sm: 'block' }, fontVariantNumeric: 'tabular-nums' }}
        >
          {[source, tool.chars !== undefined ? `${tool.chars.toLocaleString()} chars` : null].filter(Boolean).join(' · ')}
        </Typography>
        <ExpandMoreRoundedIcon
          sx={{ fontSize: 18, color: 'text.secondary', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
        />
      </ButtonBase>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ px: 1.5, pb: 1.5, pt: 0.25, display: 'grid', gap: 1 }}>
          <Pane label="Input" text={JSON.stringify(tool.arguments, null, 2)} />
          {tool.result !== undefined ? (
            <Result text={tool.result} error={tool.status === 'error'} />
          ) : (
            tool.status !== 'running' && (
              <Typography variant="caption" color="text.secondary">
                The full result appears when the turn finishes.
              </Typography>
            )
          )}
        </Box>
      </Collapse>
    </Box>
  );
}

/** One run of tool calls inside an assistant turn, summarised on one line until opened. */
export function ToolGroup({ tools, live = false }: { tools: ToolView[]; live?: boolean }) {
  const [open, setOpen] = useState(live);
  const running = tools.find((tool) => tool.status === 'running');
  const errors = tools.filter((tool) => tool.status === 'error').length;
  const runningLabel = running && (skillOf(running) ? `Loading skill ${skillOf(running)}` : `Running ${toolLabel(running.name).tool}`);
  return (
    <Box sx={{ my: 1.5, border: 1, borderColor: 'border', borderRadius: 3, bgcolor: 'background.paper', overflow: 'hidden' }}>
      <ButtonBase
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        sx={{ width: '100%', justifyContent: 'flex-start', gap: 1.25, px: 1.5, py: 1, '&:hover': { bgcolor: 'background.hover' } }}
      >
        <Box sx={{ width: 16, display: 'grid', placeItems: 'center' }}>
          {running ? (
            <CircularProgress size={14} thickness={5} />
          ) : (
            <HandymanOutlinedIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
          )}
        </Box>
        <Typography sx={{ fontSize: '0.8125rem', fontWeight: 550, flex: 1, textAlign: 'left' }}>
          {runningLabel ? `${runningLabel}...` : `Used ${tools.length} tool${tools.length === 1 ? '' : 's'}`}
        </Typography>
        {errors > 0 && (
          <Typography variant="caption" sx={{ color: 'error.main', fontWeight: 550 }}>
            {errors} failed
          </Typography>
        )}
        <ExpandMoreRoundedIcon
          sx={{ fontSize: 18, color: 'text.secondary', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
        />
      </ButtonBase>
      <Collapse in={open}>
        <Box sx={{ borderTop: 1, borderColor: 'border' }}>
          {tools.map((tool) => (
            <ToolRow key={tool.id} tool={tool} />
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}
