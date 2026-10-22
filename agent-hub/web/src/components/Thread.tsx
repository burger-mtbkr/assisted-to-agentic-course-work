import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import { keyframes } from '@mui/material/styles';
import { type ReactNode, memo } from 'react';
import { AgentAvatar } from '../agentLook';
import { type Part, liveParts, toBlocks } from '../format';
import type { AgentKey, LiveTurn, Message } from '../types';
import { CopyButton, Markdown } from './Markdown';
import { ToolGroup } from './ToolGroup';

const pulse = keyframes`
  0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-2px); }
`;

const caret = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
`;

function UserBubble({ text }: { text: string }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'flex-end', my: 3 }}>
      <Box
        sx={{
          maxWidth: { xs: '88%', sm: '78%' },
          bgcolor: 'background.bubble',
          px: 2,
          py: 1.25,
          borderRadius: '18px 18px 6px 18px',
          whiteSpace: 'pre-wrap',
          overflowWrap: 'anywhere',
          fontSize: '0.9375rem',
          lineHeight: 1.6,
        }}
      >
        {text}
      </Box>
    </Box>
  );
}

function AssistantFrame({ agent, name, children }: { agent: AgentKey; name: string; children: ReactNode }) {
  return (
    <Box sx={{ display: 'flex', gap: 1.75, my: 3, '&:hover .actions': { opacity: 1 } }}>
      <Box sx={{ pt: 0.25 }}>
        <AgentAvatar agent={agent} size={28} />
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="subtitle2" sx={{ lineHeight: '28px', mb: 0.25 }}>
          {name}
        </Typography>
        {children}
      </Box>
    </Box>
  );
}

function Parts({ parts, live }: { parts: Part[]; live?: boolean }) {
  return (
    <>
      {parts.map((part, index) =>
        part.kind === 'text' ? (
          <Markdown key={index} text={part.text} />
        ) : (
          <ToolGroup key={index} tools={part.tools} live={live} />
        ),
      )}
    </>
  );
}

function Thinking({ label }: { label: string }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, py: 0.75, color: 'text.secondary' }} role="status">
      <Box sx={{ display: 'flex', gap: 0.5 }}>
        {[0, 1, 2].map((dot) => (
          <Box
            key={dot}
            sx={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              bgcolor: 'currentColor',
              animation: `${pulse} 1.2s ${dot * 0.15}s infinite ease-in-out`,
            }}
          />
        ))}
      </Box>
      <Typography variant="body2">{label}</Typography>
    </Box>
  );
}

type ThreadProps = {
  agent: AgentKey;
  agentName: string;
  messages: Message[];
  live?: LiveTurn;
  runningElsewhere: boolean;
  onRetry: () => void;
  onEdit: () => void;
};

function ThreadView({ agent, agentName, messages, live, runningElsewhere, onRetry, onEdit }: ThreadProps) {
  const blocks = toBlocks(messages);
  const parts = live ? liveParts(live.parts) : [];
  const streamingText = parts.at(-1)?.kind === 'text';
  const toolRunning = live?.parts.some((part) => part.kind === 'tool' && part.tool.status === 'running');

  return (
    <>
      {blocks.length === 0 && !live && !runningElsewhere && (
        <Typography color="text.secondary" sx={{ textAlign: 'center', py: 10 }}>
          No messages yet. A turn that failed or was stopped is rolled back, so nothing from it was kept.
        </Typography>
      )}
      {blocks.map((block, index) => {
        if (block.kind === 'user') return <UserBubble key={index} text={block.text} />;
        if (block.kind === 'notice')
          return (
            <Box key={index} sx={{ display: 'flex', gap: 1, color: 'text.secondary', my: 2, ml: 5.75, fontSize: '0.8125rem' }}>
              <InfoOutlinedIcon sx={{ fontSize: 16, mt: 0.2 }} />
              <span>{block.text}</span>
            </Box>
          );
        const text = block.parts.flatMap((part) => (part.kind === 'text' ? [part.text] : [])).join('\n\n');
        return (
          <AssistantFrame key={index} agent={agent} name={agentName}>
            <Parts parts={block.parts} />
            {text && (
              <Box className="actions" sx={{ mt: 0.75, ml: -0.75, opacity: { xs: 1, md: 0 }, transition: 'opacity 0.15s' }}>
                <CopyButton text={text} />
              </Box>
            )}
          </AssistantFrame>
        );
      })}

      {runningElsewhere && !live && (
        <AssistantFrame agent={agent} name={agentName}>
          <Thinking label="Still working on the last message. It will appear here when it is done." />
        </AssistantFrame>
      )}

      {live && (
        <>
          <UserBubble text={live.text} />
          <AssistantFrame agent={agent} name={agentName}>
            {live.status === 'error' ? (
              <Alert
                severity="error"
                variant="outlined"
                sx={{ alignItems: 'flex-start', bgcolor: 'background.paper' }}
                action={
                  <Box sx={{ display: 'flex', gap: 0.5, pt: 0.25 }}>
                    <Button size="small" color="inherit" onClick={onEdit}>
                      Edit
                    </Button>
                    <Button size="small" variant="outlined" color="inherit" onClick={onRetry}>
                      Retry
                    </Button>
                  </Box>
                }
              >
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.25 }}>
                  This turn failed and was rolled back.
                </Typography>
                <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                  {live.error}
                </Typography>
              </Alert>
            ) : (
              <>
                <Parts parts={parts} live />
                {streamingText && live.status === 'running' && (
                  <Box
                    component="span"
                    sx={{
                      display: 'inline-block',
                      width: 7,
                      height: 16,
                      ml: 0.25,
                      verticalAlign: 'text-bottom',
                      bgcolor: 'text.primary',
                      borderRadius: 0.5,
                      animation: `${caret} 1s steps(1) infinite`,
                    }}
                  />
                )}
                {live.status === 'stopping' ? (
                  <Thinking label={toolRunning ? 'Stopping once the running tool finishes...' : 'Stopping...'} />
                ) : (
                  !streamingText && !toolRunning && <Thinking label={parts.length ? 'Thinking...' : 'Working...'} />
                )}
              </>
            )}
          </AssistantFrame>
        </>
      )}
    </>
  );
}

export const Thread = memo(ThreadView);
