import ArrowDownwardRoundedIcon from '@mui/icons-material/ArrowDownwardRounded';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Fab from '@mui/material/Fab';
import Typography from '@mui/material/Typography';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { AgentInfo, Chat, LiveTurn } from '../types';
import { Composer, type ComposerState } from './Composer';
import { Thread } from './Thread';

export const CONTENT_WIDTH = 780;

type ChatViewProps = {
  agent: AgentInfo | undefined;
  chat: Chat | null;
  live: LiveTurn | undefined;
  draft: string;
  onDraft: (value: string) => void;
  onSend: (text: string) => void;
  onStop: () => void;
  onRetry: () => void;
  onEdit: () => void;
  inputRef: React.Ref<HTMLTextAreaElement>;
};

export function ChatView({ agent, chat, live, draft, onDraft, onSend, onStop, onRetry, onEdit, inputRef }: ChatViewProps) {
  const scroller = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = (smooth = false) => {
    const element = scroller.current;
    if (element) element.scrollTo({ top: element.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  };

  useEffect(() => {
    pinned.current = true;
  }, [chat?.id]);

  useLayoutEffect(() => {
    if (pinned.current) scrollToBottom();
  }, [chat, live]);

  const runningElsewhere = !!chat?.running && !live;
  const state: ComposerState =
    live?.status === 'running' ? 'running' : live?.status === 'stopping' ? 'stopping' : !agent?.available || runningElsewhere ? 'disabled' : 'idle';
  const key = chat?.agent ?? agent?.key ?? 'pair';

  return (
    <>
      <Box
        ref={scroller}
        onScroll={(event) => {
          const element = event.currentTarget;
          pinned.current = element.scrollHeight - element.scrollTop - element.clientHeight < 96;
          setShowJump(!pinned.current);
        }}
        sx={{ flex: 1, overflowY: 'auto', position: 'relative' }}
      >
        <Box sx={{ maxWidth: CONTENT_WIDTH, mx: 'auto', px: { xs: 2, sm: 3 }, pt: 1, pb: 4 }}>
          {chat ? (
            <Thread
              agent={key}
              agentName={agent?.name ?? key}
              messages={chat.messages}
              live={live}
              runningElsewhere={runningElsewhere}
              onRetry={onRetry}
              onEdit={onEdit}
            />
          ) : (
            <Box sx={{ display: 'grid', placeItems: 'center', py: 12 }}>
              <CircularProgress size={26} />
            </Box>
          )}
        </Box>
      </Box>
      <Box sx={{ position: 'relative', maxWidth: CONTENT_WIDTH, width: '100%', mx: 'auto', px: { xs: 1.5, sm: 3 }, pb: 1.5 }}>
        {showJump && (
          <Fab
            size="small"
            aria-label="Scroll to the latest message"
            onClick={() => scrollToBottom(true)}
            sx={{
              position: 'absolute',
              top: -52,
              left: '50%',
              transform: 'translateX(-50%)',
              bgcolor: 'background.raised',
              color: 'text.primary',
              border: 1,
              borderColor: 'border',
              boxShadow: 2,
              '&:hover': { bgcolor: 'background.raised' },
            }}
          >
            <ArrowDownwardRoundedIcon fontSize="small" />
          </Fab>
        )}
        <Composer
          inputRef={inputRef}
          value={draft}
          onChange={onDraft}
          onSend={() => {
            pinned.current = true;
            onSend(draft.trim());
          }}
          onStop={onStop}
          state={state}
          placeholder={
            agent && !agent.available
              ? `${agent.name} is unavailable: ${agent.reason}`
              : runningElsewhere
                ? 'Waiting for the last message to finish...'
                : `Reply to the ${agent?.name ?? 'agent'}...`
          }
        />
        <Typography variant="caption" color="text.disabled" component="div" sx={{ textAlign: 'center', mt: 1 }}>
          Agents answer from the repo and can still be wrong. Check what matters.
        </Typography>
      </Box>
    </>
  );
}
