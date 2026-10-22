import ArrowUpwardRoundedIcon from '@mui/icons-material/ArrowUpwardRounded';
import StopRoundedIcon from '@mui/icons-material/StopRounded';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import IconButton from '@mui/material/IconButton';
import InputBase from '@mui/material/InputBase';
import Tooltip from '@mui/material/Tooltip';
import { alpha } from '@mui/material/styles';
import type { ReactNode, Ref } from 'react';

export type ComposerState = 'idle' | 'running' | 'stopping' | 'disabled';

type ComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  state: ComposerState;
  placeholder: string;
  footer?: ReactNode;
  inputRef?: Ref<HTMLTextAreaElement>;
};

export function Composer({ value, onChange, onSend, onStop, state, placeholder, footer, inputRef }: ComposerProps) {
  const busy = state === 'running' || state === 'stopping';
  const canSend = state === 'idle' && value.trim().length > 0;
  return (
    <Box
      sx={(theme) => ({
        border: 1,
        borderColor: 'borderStrong',
        borderRadius: 4,
        bgcolor: 'background.paper',
        transition: 'border-color 0.15s, box-shadow 0.15s',
        boxShadow: theme.palette.mode === 'dark' ? '0 1px 0 rgba(255,255,255,0.03) inset' : '0 1px 2px rgba(24,24,27,0.04), 0 4px 16px rgba(24,24,27,0.04)',
        '&:focus-within': {
          borderColor: alpha(theme.palette.primary.main, 0.6),
          boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.12)}`,
        },
      })}
    >
      <InputBase
        inputRef={inputRef}
        autoFocus
        multiline
        minRows={1}
        maxRows={12}
        fullWidth
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            if (canSend) onSend();
          } else if (event.key === 'Escape' && state === 'running') {
            onStop();
          }
        }}
        sx={{ px: 2, pt: 1.6, pb: 0.5, fontSize: '0.9375rem', lineHeight: 1.6 }}
        slotProps={{ input: { 'aria-label': 'Message' } }}
      />
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 1, pb: 1, pl: 1.5, minHeight: 44 }}>
        <Box sx={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 1 }}>{footer}</Box>
        {busy ? (
          <Tooltip title={state === 'stopping' ? 'Stopping...' : 'Stop (Esc)'}>
            <span>
              <IconButton
                onClick={onStop}
                disabled={state === 'stopping'}
                aria-label="Stop"
                size="small"
                sx={{
                  width: 32,
                  height: 32,
                  bgcolor: 'text.primary',
                  color: 'background.paper',
                  '&:hover': { bgcolor: 'text.secondary' },
                  '&.Mui-disabled': { bgcolor: 'action.disabledBackground' },
                }}
              >
                {state === 'stopping' ? <CircularProgress size={14} thickness={5} /> : <StopRoundedIcon sx={{ fontSize: 18 }} />}
              </IconButton>
            </span>
          </Tooltip>
        ) : (
          <Tooltip title="Send (Enter)">
            <span>
              <IconButton
                onClick={onSend}
                disabled={!canSend}
                aria-label="Send"
                size="small"
                sx={{
                  width: 32,
                  height: 32,
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  '&:hover': { bgcolor: 'primary.main', filter: 'brightness(1.08)' },
                  '&.Mui-disabled': { bgcolor: 'action.disabledBackground', color: 'action.disabled' },
                }}
              >
                <ArrowUpwardRoundedIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </span>
          </Tooltip>
        )}
      </Box>
    </Box>
  );
}
