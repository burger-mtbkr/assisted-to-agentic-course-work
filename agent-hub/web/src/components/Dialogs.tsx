import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import ButtonBase from '@mui/material/ButtonBase';
import Chip from '@mui/material/Chip';
import Collapse from '@mui/material/Collapse';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { type ReactNode, useState } from 'react';
import { AgentAvatar } from '../agentLook';
import { formatTokens } from '../format';
import { MONO } from '../theme';
import type { AgentInfo, Chat, Message } from '../types';
import { CopyButton } from './Markdown';

function Title({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <DialogTitle sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, pr: 1.5, pb: 1.5 }}>
      <Box sx={{ flex: 1, minWidth: 0 }}>{children}</Box>
      <IconButton onClick={onClose} aria-label="Close" size="small">
        <CloseRoundedIcon fontSize="small" />
      </IconButton>
    </DialogTitle>
  );
}

export function RenameDialog({ initial, onClose, onSave }: { initial: string; onClose: () => void; onSave: (title: string) => void }) {
  const [title, setTitle] = useState(initial);
  const save = () => title.trim() && onSave(title.trim());
  return (
    <Dialog open onClose={onClose} maxWidth="xs">
      <DialogTitle>Rename chat</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          size="small"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          onKeyDown={(event) => event.key === 'Enter' && save()}
          onFocus={(event) => event.target.select()}
          slotProps={{ htmlInput: { maxLength: 200, 'aria-label': 'Chat title' } }}
          sx={{ mt: 0.5 }}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        <Button onClick={onClose} color="inherit">
          Cancel
        </Button>
        <Button onClick={save} variant="contained" disabled={!title.trim()}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function DeleteDialog({ title, onClose, onDelete }: { title: string; onClose: () => void; onDelete: () => void }) {
  return (
    <Dialog open onClose={onClose} maxWidth="xs">
      <DialogTitle>Delete chat?</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary">
          <Box component="strong" sx={{ color: 'text.primary' }}>
            {title || 'Untitled'}
          </Box>{' '}
          and its whole conversation will be deleted. Export it first if you want to keep a copy.
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        <Button onClick={onClose} color="inherit">
          Cancel
        </Button>
        <Button onClick={onDelete} variant="contained" color="error">
          Delete
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function Entry({ name, description, tag }: { name: string; description: string; tag?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <ButtonBase
      onClick={() => setOpen(!open)}
      sx={{ display: 'block', width: '100%', textAlign: 'left', py: 1.25, px: 1, borderRadius: 2, '&:hover': { bgcolor: 'background.hover' } }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography sx={{ fontFamily: MONO, fontSize: '0.8rem', fontWeight: 600 }}>{name}</Typography>
        {tag && <Chip label={tag} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.6875rem' }} />}
      </Box>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={open ? { mt: 0.5, whiteSpace: 'pre-wrap' } : { mt: 0.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
      >
        {description}
      </Typography>
    </ButtonBase>
  );
}

export function AgentDialog({ agent, onClose }: { agent: AgentInfo; onClose: () => void }) {
  const [tab, setTab] = useState(0);
  const tools = agent.tools ?? [];
  const skills = agent.skills ?? [];
  return (
    <Dialog open onClose={onClose} maxWidth="md" scroll="paper" slotProps={{ paper: { sx: { height: 'min(720px, 90vh)' } } }}>
      <Title onClose={onClose}>
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
          <AgentAvatar agent={agent.key} size={36} />
          <Box>
            <Typography variant="h6" component="div">
              {agent.name}{' '}
              <Typography component="span" variant="body2" color="text.secondary">
                {agent.module}
              </Typography>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {agent.summary}
            </Typography>
          </Box>
        </Box>
      </Title>
      <Tabs value={tab} onChange={(_, value: number) => setTab(value)} sx={{ px: 3, minHeight: 40, borderBottom: 1, borderColor: 'border', '& .MuiTab-root': { minHeight: 40, px: 1.5, minWidth: 0 } }}>
        <Tab label={`Tools (${tools.length})`} />
        <Tab label={`Skills (${skills.length})`} />
        <Tab label="System prompt" />
      </Tabs>
      <DialogContent sx={{ px: 2 }}>
        {tab === 0 &&
          tools.map((tool) => (
            <Entry key={tool.name} name={tool.name} description={tool.description} tag={tool.source.replace(/^mcp:/, 'mcp · ')} />
          ))}
        {tab === 1 && (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ px: 1, pb: 1 }}>
              The agent sees only these names and descriptions until a request matches one; then it loads the skill in full.
            </Typography>
            {skills.map((skill) => (
              <Entry key={skill.name} name={skill.name} description={skill.description} />
            ))}
          </>
        )}
        {tab === 2 && (
          <Box sx={{ px: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
              <CopyButton text={agent.system_prompt ?? ''} />
            </Box>
            <Box
              component="pre"
              sx={{ m: 0, p: 2, fontFamily: MONO, fontSize: '0.78rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', bgcolor: 'background.code', border: 1, borderColor: 'border', borderRadius: 2 }}
            >
              {agent.system_prompt}
            </Box>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}

function preview(message: Message): string {
  if (message.role === 'tool') return `${message.name} · ${message.is_error ? 'error · ' : ''}${message.content.length.toLocaleString()} chars`;
  const calls = message.role === 'assistant' ? (message.tool_calls ?? []).map((call) => call.name) : [];
  const text = message.content.replace(/\s+/g, ' ').trim();
  return [text.length > 160 ? `${text.slice(0, 160)}...` : text, calls.length ? `calls ${calls.join(', ')}` : ''].filter(Boolean).join('  ·  ');
}

const ROLE_COLOURS: Record<string, 'default' | 'primary' | 'secondary' | 'warning'> = { system: 'secondary', user: 'primary', tool: 'warning' };

function MemoryRow({ index, role, label, raw }: { index: number; role: string; label: string; raw: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Box sx={{ borderBottom: 1, borderColor: 'border' }}>
      <ButtonBase onClick={() => setOpen(!open)} sx={{ width: '100%', justifyContent: 'flex-start', gap: 1.5, py: 1, px: 1, textAlign: 'left', '&:hover': { bgcolor: 'background.hover' } }}>
        <Typography sx={{ fontFamily: MONO, fontSize: '0.75rem', color: 'text.secondary', width: 24, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
          {index}
        </Typography>
        <Chip label={role} size="small" color={ROLE_COLOURS[role] ?? 'default'} variant="outlined" sx={{ width: 78 }} />
        <Typography noWrap sx={{ flex: 1, fontSize: '0.8125rem', minWidth: 0 }}>
          {label}
        </Typography>
        <ExpandMoreRoundedIcon sx={{ fontSize: 18, color: 'text.secondary', transform: open ? 'rotate(180deg)' : 'none' }} />
      </ButtonBase>
      <Collapse in={open} unmountOnExit>
        <Box component="pre" sx={{ m: 0, mb: 1.25, p: 1.5, maxHeight: 380, overflow: 'auto', fontFamily: MONO, fontSize: '0.75rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', bgcolor: 'background.code', border: 1, borderColor: 'border', borderRadius: 2 }}>
          {raw}
        </Box>
      </Collapse>
    </Box>
  );
}

export function MemoryDialog({ agent, chat, onClose }: { agent: AgentInfo; chat: Chat; onClose: () => void }) {
  return (
    <Dialog open onClose={onClose} maxWidth="md" scroll="paper" slotProps={{ paper: { sx: { height: 'min(720px, 90vh)' } } }}>
      <Title onClose={onClose}>
        <Typography variant="h6">Working memory</Typography>
        <Typography variant="body2" color="text.secondary">
          What {agent.name} is sent on every model call: its system prompt and this chat so far. {chat.messages.length + 1} messages ·{' '}
          {formatTokens(chat.usage.input_tokens)} tokens in, {formatTokens(chat.usage.output_tokens)} out in completed turns.
        </Typography>
      </Title>
      <DialogContent dividers sx={{ py: 0, px: 2 }}>
        <MemoryRow index={0} role="system" label={(agent.system_prompt ?? '').replace(/\s+/g, ' ').slice(0, 160)} raw={agent.system_prompt ?? ''} />
        {chat.messages.map((message, index) => (
          <MemoryRow
            key={index}
            index={index + 1}
            role={message.role}
            label={preview(message)}
            raw={message.role === 'tool' ? message.content : JSON.stringify(message, null, 2)}
          />
        ))}
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 1.5 }}>
        <Typography variant="caption" color="text.secondary" sx={{ flex: 1 }}>
          The raw state is the agent's own format, which the chat resumes from.
        </Typography>
        <CopyButton text={JSON.stringify(chat.state, null, 2)} label="Copy raw state" />
      </DialogActions>
    </Dialog>
  );
}
