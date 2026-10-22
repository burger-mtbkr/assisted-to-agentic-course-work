import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import DarkModeOutlinedIcon from '@mui/icons-material/DarkModeOutlined';
import KeyboardArrowDownRoundedIcon from '@mui/icons-material/KeyboardArrowDownRounded';
import LightModeOutlinedIcon from '@mui/icons-material/LightModeOutlined';
import SettingsBrightnessOutlinedIcon from '@mui/icons-material/SettingsBrightnessOutlined';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useState } from 'react';
import { AgentAvatar } from '../agentLook';
import type { ModePreference } from '../theme';
import type { AgentInfo, AgentKey } from '../types';

function useMenu() {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  return { anchor, open: (event: { currentTarget: HTMLElement }) => setAnchor(event.currentTarget), close: () => setAnchor(null) };
}

/** The free-tier models; each has its own daily quota, so switching is the way past a 429. */
export function ModelPicker({ agent, onChange }: { agent: AgentInfo; onChange: (model: string) => void }) {
  const menu = useMenu();
  if (!agent.model) return null;
  return (
    <>
      <Tooltip title={agent.kind === 'workflow' ? "The Mechanic's model (the Doctor and Librarian steps call none)" : 'Model for this agent (free tier: switch when one runs out of quota)'}>
        <Button
          size="small"
          color="inherit"
          onClick={menu.open}
          endIcon={<KeyboardArrowDownRoundedIcon />}
          aria-label="Model"
          sx={{ color: 'text.secondary', fontWeight: 500, '& .MuiButton-endIcon': { ml: 0.25 } }}
        >
          {agent.model}
        </Button>
      </Tooltip>
      <Menu anchorEl={menu.anchor} open={!!menu.anchor} onClose={menu.close}>
        <Typography variant="overline" color="text.secondary" sx={{ px: 1.25, display: 'block' }}>
          Free-tier models
        </Typography>
        {(agent.models ?? []).map((model) => (
          <MenuItem
            key={model}
            selected={model === agent.model}
            onClick={() => {
              menu.close();
              if (model !== agent.model) onChange(model);
            }}
          >
            <ListItemIcon>{model === agent.model && <CheckRoundedIcon fontSize="small" />}</ListItemIcon>
            {model}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}

/** Which agent a new chat talks to. */
export function AgentPicker({
  agents,
  value,
  onChange,
}: {
  agents: AgentInfo[];
  value: AgentKey;
  onChange: (agent: AgentKey) => void;
}) {
  const menu = useMenu();
  const current = agents.find((agent) => agent.key === value);
  return (
    <>
      <Button
        size="small"
        color="inherit"
        onClick={menu.open}
        aria-label="Agent"
        startIcon={<AgentAvatar agent={value} size={20} />}
        endIcon={<KeyboardArrowDownRoundedIcon />}
        sx={{ fontWeight: 550, pl: 0.75, '& .MuiButton-startIcon': { mr: 0.75 }, '& .MuiButton-endIcon': { ml: 0.25 } }}
      >
        {current?.name ?? value}
      </Button>
      <Menu
        anchorEl={menu.anchor}
        open={!!menu.anchor}
        onClose={menu.close}
        anchorOrigin={{ vertical: 'top', horizontal: 'left' }}
        transformOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        slotProps={{ paper: { sx: { width: 340, mt: -0.5 } } }}
      >
        {agents
          .filter((agent) => agent.kind === 'chat')
          .map((agent) => (
            <MenuItem
              key={agent.key}
              selected={agent.key === value}
              disabled={!agent.available}
              onClick={() => {
                menu.close();
                onChange(agent.key);
              }}
              sx={{ alignItems: 'flex-start', gap: 1.25, py: 1, whiteSpace: 'normal' }}
            >
              <AgentAvatar agent={agent.key} size={28} />
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="subtitle2">
                  {agent.name}{' '}
                  <Typography component="span" variant="caption" color="text.secondary">
                    {agent.module}
                  </Typography>
                </Typography>
                <Typography variant="caption" color="text.secondary" component="div">
                  {agent.available ? agent.summary : `Unavailable: ${agent.reason}`}
                </Typography>
              </Box>
              {agent.key === value && <CheckRoundedIcon fontSize="small" sx={{ mt: 0.5 }} />}
            </MenuItem>
          ))}
      </Menu>
    </>
  );
}

const MODES: { value: ModePreference; label: string; icon: typeof LightModeOutlinedIcon }[] = [
  { value: 'light', label: 'Light', icon: LightModeOutlinedIcon },
  { value: 'dark', label: 'Dark', icon: DarkModeOutlinedIcon },
  { value: 'system', label: 'System', icon: SettingsBrightnessOutlinedIcon },
];

export function ThemeMenu({ value, onChange }: { value: ModePreference; onChange: (mode: ModePreference) => void }) {
  const menu = useMenu();
  const Current = MODES.find((mode) => mode.value === value)!.icon;
  return (
    <>
      <Tooltip title="Appearance">
        <IconButton size="small" onClick={menu.open} aria-label="Appearance">
          <Current fontSize="small" />
        </IconButton>
      </Tooltip>
      <Menu anchorEl={menu.anchor} open={!!menu.anchor} onClose={menu.close}>
        {MODES.map(({ value: mode, label, icon: Icon }) => (
          <MenuItem
            key={mode}
            selected={mode === value}
            onClick={() => {
              menu.close();
              onChange(mode);
            }}
          >
            <ListItemIcon>
              <Icon fontSize="small" />
            </ListItemIcon>
            <Box sx={{ flex: 1, pr: 2 }}>{label}</Box>
            {mode === value && <CheckRoundedIcon fontSize="small" />}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
