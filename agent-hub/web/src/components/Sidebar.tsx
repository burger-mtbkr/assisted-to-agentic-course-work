import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import DriveFileRenameOutlineIcon from '@mui/icons-material/DriveFileRenameOutline';
import EditSquareIcon from '@mui/icons-material/EditSquare';
import FileUploadOutlinedIcon from '@mui/icons-material/FileUploadOutlined';
import MoreHorizRoundedIcon from '@mui/icons-material/MoreHorizRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import ViewSidebarOutlinedIcon from '@mui/icons-material/ViewSidebarOutlined';
import Box from '@mui/material/Box';
import ButtonBase from '@mui/material/ButtonBase';
import CircularProgress from '@mui/material/CircularProgress';
import IconButton from '@mui/material/IconButton';
import InputBase from '@mui/material/InputBase';
import ListItemIcon from '@mui/material/ListItemIcon';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { type ReactNode, type Ref, useRef, useState } from 'react';
import { AgentAvatar } from '../agentLook';
import { groupByDate } from '../format';
import type { AgentInfo, AgentKey, ChatSummary } from '../types';

export const SIDEBAR_WIDTH = 288;

type SidebarProps = {
  agents: AgentInfo[];
  chats: ChatSummary[];
  activeChatId: string | null;
  teamActive: boolean;
  isRunning: (chat: ChatSummary) => boolean;
  onNewChat: (agent?: AgentKey) => void;
  onOpenTeam: () => void;
  onSelect: (id: string) => void;
  onRename: (chat: ChatSummary) => void;
  onExport: (chat: ChatSummary) => void;
  onDelete: (chat: ChatSummary) => void;
  onImport: (file: File) => void;
  onClose: () => void;
  searchRef: Ref<HTMLInputElement>;
};

function Row({
  selected,
  onClick,
  children,
  trailing,
  disabled,
}: {
  selected?: boolean;
  onClick: () => void;
  children: ReactNode;
  trailing?: ReactNode;
  disabled?: boolean;
}) {
  return (
    <Box
      sx={{
        position: 'relative',
        borderRadius: 2,
        bgcolor: selected ? 'action.selected' : 'transparent',
        '&:hover': { bgcolor: selected ? 'action.selected' : 'background.hover' },
        '& .trailing': { opacity: selected ? 1 : 0 },
        '&:hover .trailing, & .trailing:focus-within': { opacity: 1 },
      }}
    >
      <ButtonBase
        onClick={onClick}
        disabled={disabled}
        sx={{ width: '100%', justifyContent: 'flex-start', gap: 1.25, pl: 1.25, pr: trailing ? 5 : 1.25, py: 0.85, borderRadius: 2, textAlign: 'left', opacity: disabled ? 0.5 : 1 }}
      >
        {children}
      </ButtonBase>
      {trailing && (
        <Box className="trailing" sx={{ position: 'absolute', right: 4, top: '50%', transform: 'translateY(-50%)', display: 'flex', alignItems: 'center' }}>
          {trailing}
        </Box>
      )}
    </Box>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <Typography variant="overline" color="text.secondary" sx={{ display: 'block', px: 1.25, pt: 1.5, pb: 0.25 }}>
      {children}
    </Typography>
  );
}

export function Sidebar(props: SidebarProps) {
  const { agents, chats, activeChatId, teamActive, isRunning, onNewChat, onOpenTeam, onSelect, onImport, onClose, searchRef } = props;
  const [query, setQuery] = useState('');
  const [menu, setMenu] = useState<{ anchor: HTMLElement; chat: ChatSummary } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const names = Object.fromEntries(agents.map((agent) => [agent.key, agent.name]));

  const needle = query.trim().toLowerCase();
  const shown = needle
    ? chats.filter((chat) => `${chat.title || 'Untitled'} ${names[chat.agent] ?? ''}`.toLowerCase().includes(needle))
    : chats;
  const act = (action: (chat: ChatSummary) => void) => () => {
    if (menu) action(menu.chat);
    setMenu(null);
  };
  const ready = agents.filter((agent) => agent.available).length;

  return (
    <Box component="nav" aria-label="Chats and agents" sx={{ width: SIDEBAR_WIDTH, height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.sidebar', borderRight: 1, borderColor: 'border' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, px: 2, pt: 1.75, pb: 1 }}>
        <Box
          sx={{
            width: 28,
            height: 28,
            borderRadius: '8px',
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 7px)',
            gap: '3px',
            placeContent: 'center',
            bgcolor: 'primary.main',
            '& span': { width: 7, height: 7, borderRadius: '50%', bgcolor: 'primary.contrastText' },
            '& span:nth-of-type(2), & span:nth-of-type(3)': { opacity: 0.7 },
            '& span:nth-of-type(4)': { opacity: 0.45 },
          }}
          aria-hidden
        >
          <span />
          <span />
          <span />
          <span />
        </Box>
        <Typography sx={{ fontWeight: 650, flex: 1, letterSpacing: '-0.01em' }}>Agent Hub</Typography>
        <Tooltip title="Close sidebar">
          <IconButton size="small" onClick={onClose} aria-label="Close sidebar">
            <ViewSidebarOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ px: 1, pb: 0.5 }}>
        <Row onClick={() => onNewChat()}>
          <EditSquareIcon sx={{ fontSize: 18, color: 'text.secondary', mx: 0.5 }} />
          <Typography variant="body2" sx={{ fontWeight: 550, flex: 1 }}>
            New chat
          </Typography>
          <Typography variant="caption" color="text.disabled">
            Ctrl+Shift+O
          </Typography>
        </Row>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mx: 0.25, mt: 0.5, px: 1.25, py: 0.6, borderRadius: 2, border: 1, borderColor: 'border', bgcolor: 'background.paper' }}>
          <SearchRoundedIcon sx={{ fontSize: 17, color: 'text.secondary' }} />
          <InputBase
            inputRef={searchRef}
            fullWidth
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => event.key === 'Escape' && setQuery('')}
            placeholder="Search chats"
            sx={{ fontSize: '0.8125rem' }}
            slotProps={{ input: { 'aria-label': 'Search chats' } }}
          />
          <Typography variant="caption" color="text.disabled" sx={{ whiteSpace: 'nowrap' }}>
            Ctrl+K
          </Typography>
        </Box>
      </Box>

      <Box sx={{ flex: 1, overflowY: 'auto', px: 1, pb: 1 }}>
        <SectionLabel>Agents</SectionLabel>
        {agents.map((agent) => (
          <Tooltip key={agent.key} title={agent.available ? agent.summary : `Unavailable: ${agent.reason}`} placement="right">
            <Box>
              <Row
                selected={agent.key === 'team' && teamActive}
                disabled={!agent.available}
                onClick={() => (agent.kind === 'workflow' ? onOpenTeam() : onNewChat(agent.key))}
              >
                <AgentAvatar agent={agent.key} size={24} />
                <Typography variant="body2" sx={{ fontWeight: 500, flex: 1 }} noWrap>
                  {agent.name}
                </Typography>
                <Typography variant="caption" color="text.disabled" noWrap>
                  {agent.available ? agent.module : 'unavailable'}
                </Typography>
              </Row>
            </Box>
          </Tooltip>
        ))}

        {shown.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ px: 1.25, py: 2 }}>
            {needle ? 'No chats match.' : 'Your chats appear here.'}
          </Typography>
        ) : (
          groupByDate(shown).map(([label, group]) => (
            <Box key={label}>
              <SectionLabel>{label}</SectionLabel>
              {group.map((chat) => {
                const running = isRunning(chat);
                return (
                  <Row
                    key={chat.id}
                    selected={chat.id === activeChatId}
                    onClick={() => onSelect(chat.id)}
                    trailing={
                      <IconButton
                        size="small"
                        aria-label={`Options for ${chat.title || 'Untitled'}`}
                        onClick={(event) => setMenu({ anchor: event.currentTarget, chat })}
                        sx={{ width: 28, height: 28 }}
                      >
                        <MoreHorizRoundedIcon fontSize="small" />
                      </IconButton>
                    }
                  >
                    <AgentAvatar agent={chat.agent} size={20} />
                    <Typography variant="body2" noWrap sx={{ flex: 1, minWidth: 0 }}>
                      {chat.title || 'Untitled'}
                    </Typography>
                    {running && <CircularProgress size={12} thickness={6} sx={{ flexShrink: 0 }} aria-label="Working" />}
                  </Row>
                );
              })}
            </Box>
          ))
        )}
      </Box>

      <Box sx={{ borderTop: 1, borderColor: 'border', px: 1, py: 1 }}>
        <Row onClick={() => fileInput.current?.click()}>
          <FileUploadOutlinedIcon sx={{ fontSize: 18, color: 'text.secondary', mx: 0.5 }} />
          <Typography variant="body2" color="text.secondary">
            Import a chat
          </Typography>
        </Row>
        <input
          ref={fileInput}
          type="file"
          accept="application/json,.json"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onImport(file);
            event.target.value = '';
          }}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 1.5, pt: 0.75 }}>
          <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: ready === agents.length ? 'success.main' : 'warning.main' }} />
          <Typography variant="caption" color="text.secondary">
            {agents.length ? `${ready} of ${agents.length} agents ready` : 'Connecting...'}
          </Typography>
        </Box>
      </Box>

      <Menu anchorEl={menu?.anchor} open={!!menu} onClose={() => setMenu(null)}>
        <MenuItem onClick={act(props.onRename)}>
          <ListItemIcon>
            <DriveFileRenameOutlineIcon fontSize="small" />
          </ListItemIcon>
          Rename
        </MenuItem>
        <MenuItem onClick={act(props.onExport)}>
          <ListItemIcon>
            <DownloadRoundedIcon fontSize="small" />
          </ListItemIcon>
          Export
        </MenuItem>
        <MenuItem onClick={act(props.onDelete)} disabled={!!menu && isRunning(menu.chat)} sx={{ color: 'error.main' }}>
          <ListItemIcon>
            <DeleteOutlinedIcon fontSize="small" sx={{ color: 'error.main' }} />
          </ListItemIcon>
          Delete
        </MenuItem>
      </Menu>
    </Box>
  );
}
