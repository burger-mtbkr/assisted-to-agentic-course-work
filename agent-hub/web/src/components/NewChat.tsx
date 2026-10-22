import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import Box from '@mui/material/Box';
import ButtonBase from '@mui/material/ButtonBase';
import Typography from '@mui/material/Typography';
import { alpha } from '@mui/material/styles';
import { AgentAvatar, LOOKS, useAccent } from '../agentLook';
import type { AgentInfo, AgentKey } from '../types';
import { Composer } from './Composer';
import { AgentPicker } from './Pickers';

function greeting(): string {
  const hour = new Date().getHours();
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
}

function AgentCard({ agent, selected, onClick }: { agent: AgentInfo; selected: boolean; onClick: () => void }) {
  const accent = useAccent(agent.key);
  const workflow = agent.kind === 'workflow';
  return (
    <ButtonBase
      onClick={onClick}
      disabled={!agent.available}
      aria-pressed={workflow ? undefined : selected}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: 1,
        p: 1.75,
        textAlign: 'left',
        borderRadius: 3,
        border: 1,
        borderColor: selected ? alpha(accent, 0.55) : 'border',
        bgcolor: selected ? alpha(accent, 0.06) : 'background.paper',
        boxShadow: selected ? `0 0 0 3px ${alpha(accent, 0.12)}` : 'none',
        transition: 'border-color 0.15s, background-color 0.15s, box-shadow 0.15s',
        opacity: agent.available ? 1 : 0.55,
        '&:hover': { borderColor: selected ? alpha(accent, 0.55) : 'borderStrong' },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, width: '100%' }}>
        <AgentAvatar agent={agent.key} size={32} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" noWrap sx={{ lineHeight: 1.3 }}>
            {agent.name}
          </Typography>
          <Typography variant="caption" color="text.disabled" component="div" sx={{ lineHeight: 1.3 }}>
            {agent.module}
            {workflow ? ' · workflow' : ''}
          </Typography>
        </Box>
        {workflow && <ArrowForwardRoundedIcon sx={{ fontSize: 16, color: 'text.secondary' }} />}
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.5 }}>
        {agent.available ? agent.summary : `Unavailable: ${agent.reason}`}
      </Typography>
    </ButtonBase>
  );
}

type NewChatProps = {
  agents: AgentInfo[];
  agent: AgentKey;
  onAgent: (agent: AgentKey) => void;
  onOpenTeam: () => void;
  draft: string;
  onDraft: (value: string) => void;
  onSend: (text: string) => void;
  inputRef: React.Ref<HTMLTextAreaElement>;
};

export function NewChat({ agents, agent, onAgent, onOpenTeam, draft, onDraft, onSend, inputRef }: NewChatProps) {
  const current = agents.find((a) => a.key === agent);
  const available = !!current?.available;
  return (
    <Box sx={{ flex: 1, overflowY: 'auto', display: 'flex' }}>
      <Box sx={{ maxWidth: 760, width: '100%', m: 'auto', px: { xs: 2, sm: 3 }, py: 6 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1.5, mb: 1 }}>
          <AgentAvatar agent={agent} size={40} />
          <Typography variant="h4" component="h1" sx={{ fontSize: { xs: '1.6rem', sm: '2rem' } }}>
            {greeting()}
          </Typography>
        </Box>
        <Typography color="text.secondary" sx={{ textAlign: 'center', mb: 4 }}>
          Pick an agent for this chat, then ask. Each one works on config-service its own way.
        </Typography>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, gap: 1.25, mb: 2.5 }}>
          {agents.map((a) => (
            <AgentCard key={a.key} agent={a} selected={a.key === agent} onClick={() => (a.kind === 'workflow' ? onOpenTeam() : onAgent(a.key))} />
          ))}
        </Box>

        <Composer
          inputRef={inputRef}
          value={draft}
          onChange={onDraft}
          onSend={() => onSend(draft.trim())}
          onStop={() => undefined}
          state={available ? 'idle' : 'disabled'}
          placeholder={available ? LOOKS[agent].placeholder : `${current?.name ?? 'This agent'} is unavailable: ${current?.reason ?? ''}`}
          footer={<AgentPicker agents={agents} value={agent} onChange={onAgent} />}
        />

        {available && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center', mt: 2.5 }}>
            {LOOKS[agent].suggestions.map((suggestion) => (
              <ButtonBase
                key={suggestion}
                onClick={() => onSend(suggestion)}
                sx={{
                  px: 1.5,
                  py: 0.75,
                  borderRadius: 2.5,
                  border: 1,
                  borderColor: 'border',
                  bgcolor: 'background.paper',
                  fontSize: '0.8125rem',
                  color: 'text.secondary',
                  '&:hover': { color: 'text.primary', borderColor: 'borderStrong' },
                }}
              >
                {suggestion}
              </ButtonBase>
            ))}
          </Box>
        )}
      </Box>
    </Box>
  );
}
