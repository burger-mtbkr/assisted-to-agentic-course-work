import AddRoundedIcon from '@mui/icons-material/AddRounded';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import ButtonBase from '@mui/material/ButtonBase';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Radio from '@mui/material/Radio';
import Typography from '@mui/material/Typography';
import { useCallback, useEffect, useState } from 'react';
import { AgentAvatar } from '../agentLook';
import { api } from '../api';
import { shortTask } from '../format';
import type { AgentInfo, RunSummary } from '../types';
import { RunChip } from './parts';
import { RunDetail } from './RunDetail';

const FLOW = [
  ['Doctor', 'runs the API tests and lint on a fresh copy of config-service and diagnoses any failure.'],
  ['Librarian', 'gathers the decision notes, files and history a repair needs, and proposes an edit boundary.'],
  ['You', 'approve, narrow or reject that boundary. Nothing is edited before you decide.'],
  ['Mechanic', 'makes the smallest repair inside the approved paths, in the copy only.'],
  ['Doctor', 're-runs the checks to verify, and 23 coordination evals score the whole run.'],
];

function NewRunDialog({ agent, onClose, onStart }: { agent: AgentInfo; onClose: () => void; onStart: (scenario: string | null) => Promise<void> }) {
  const [scenario, setScenario] = useState<string | null>(agent.scenarios?.[0]?.name ?? null);
  const [busy, setBusy] = useState(false);
  const options = [{ name: null as string | null, description: 'Check config-service as it is. If every check passes, the run ends healthy.' }, ...(agent.scenarios ?? [])];
  return (
    <Dialog open onClose={onClose} maxWidth="sm">
      <DialogTitle>Start a repair run</DialogTitle>
      <DialogContent sx={{ display: 'grid', gap: 1 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          The run works on its own copy of config-service. A seeded regression gives the team something to repair; it is
          applied to the copy, never the original.
        </Typography>
        {options.map((option) => (
          <ButtonBase
            key={option.name ?? 'none'}
            onClick={() => setScenario(option.name)}
            sx={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'flex-start', gap: 1, p: 1.25, borderRadius: 2.5, border: 1, borderColor: scenario === option.name ? 'primary.main' : 'border', textAlign: 'left' }}
          >
            <Radio checked={scenario === option.name} size="small" sx={{ p: 0.25 }} tabIndex={-1} />
            <Box>
              <Typography variant="subtitle2">{option.name ?? 'No seeded regression'}</Typography>
              <Typography variant="caption" color="text.secondary">{option.description}</Typography>
            </Box>
          </ButtonBase>
        ))}
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
          A run makes several Gemini calls per step and runs the .NET test suite twice; it takes a few minutes.
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        <Button color="inherit" onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          disabled={busy}
          startIcon={busy ? <CircularProgress size={14} color="inherit" /> : undefined}
          onClick={async () => {
            setBusy(true);
            try {
              await onStart(scenario);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? 'Copying the codebase...' : 'Start run'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function Explainer({ onNew, available }: { onNew: () => void; available: boolean }) {
  return (
    <Box sx={{ maxWidth: 640, mx: 'auto', px: 3, py: 8 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
        <AgentAvatar agent="team" size={40} />
        <Typography variant="h4" component="h1" sx={{ fontSize: { xs: '1.6rem', sm: '2rem' } }}>Codebase Team</Typography>
      </Box>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        A repair workflow with a human gate, not agents chatting. Each step hands a written artifact to the next.
      </Typography>
      <Box component="ol" sx={{ m: 0, p: 0, listStyle: 'none', display: 'grid', gap: 1.25, mb: 3.5 }}>
        {FLOW.map(([who, what], index) => (
          <Box component="li" key={index} sx={{ display: 'flex', gap: 1.5 }}>
            <Box sx={{ width: 24, height: 24, borderRadius: '50%', bgcolor: 'background.hover', border: 1, borderColor: 'border', display: 'grid', placeItems: 'center', fontSize: '0.75rem', fontWeight: 650, flexShrink: 0 }}>
              {index + 1}
            </Box>
            <Typography variant="body2" sx={{ pt: 0.25 }}>
              <strong>{who}</strong> {what}
            </Typography>
          </Box>
        ))}
      </Box>
      <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={onNew} disabled={!available}>
        Start a repair run
      </Button>
    </Box>
  );
}

export function TeamView({ agent, taskId, onSelect, onError }: { agent: AgentInfo | undefined; taskId: string | null; onSelect: (task: string | null) => void; onError: (message: string) => void }) {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [creating, setCreating] = useState(false);
  const available = !!agent?.available;

  const refresh = useCallback(() => {
    if (!available) return;
    api.runs().then(setRuns, (exc) => onError(exc instanceof Error ? exc.message : String(exc)));
  }, [available, onError]);

  useEffect(refresh, [refresh]);
  useEffect(() => {
    if (!runs?.some((run) => run.state === 'running')) return;
    const timer = setTimeout(refresh, 4000);
    return () => clearTimeout(timer);
  }, [runs, refresh]);

  return (
    <Box sx={{ flex: 1, minHeight: 0, display: 'flex' }}>
      <Box sx={{ width: 300, flexShrink: 0, borderRight: 1, borderColor: 'border', display: { xs: taskId ? 'none' : 'flex', md: 'flex' }, flexDirection: 'column', minHeight: 0, ...(taskId ? {} : { width: { xs: '100%', md: 300 } }) }}>
        <Box sx={{ display: 'flex', alignItems: 'center', px: 2, py: 1.5, gap: 1 }}>
          <Typography variant="subtitle2" sx={{ flex: 1 }}>Repair runs</Typography>
          <Button size="small" variant="outlined" color="inherit" startIcon={<AddRoundedIcon />} onClick={() => setCreating(true)} disabled={!available}>
            New run
          </Button>
        </Box>
        <Box sx={{ flex: 1, overflowY: 'auto', px: 1, pb: 1 }}>
          {!available && <Typography variant="body2" color="text.secondary" sx={{ px: 1.25 }}>Unavailable: {agent?.reason}</Typography>}
          {available && !runs && <Box sx={{ display: 'grid', placeItems: 'center', py: 4 }}><CircularProgress size={22} /></Box>}
          {runs?.length === 0 && <Typography variant="body2" color="text.secondary" sx={{ px: 1.25 }}>No runs yet.</Typography>}
          {runs?.map((run) => (
            <ButtonBase
              key={run.task_id}
              onClick={() => onSelect(run.task_id)}
              sx={{ display: 'block', width: '100%', textAlign: 'left', px: 1.25, py: 1, borderRadius: 2, bgcolor: run.task_id === taskId ? 'action.selected' : 'transparent', '&:hover': { bgcolor: run.task_id === taskId ? 'action.selected' : 'background.hover' } }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
                <Typography variant="body2" sx={{ fontWeight: 550, flex: 1 }} noWrap>
                  {run.scenario ? run.scenario.replace(/-/g, ' ') : 'Health check'}
                </Typography>
                <RunChip run={run} />
              </Box>
              <Typography variant="caption" color="text.secondary">{shortTask(run.task_id)}</Typography>
            </ButtonBase>
          ))}
        </Box>
      </Box>
      <Box sx={{ flex: 1, minWidth: 0, overflowY: 'auto', display: { xs: taskId ? 'block' : 'none', md: 'block' } }}>
        {taskId ? <RunDetail taskId={taskId} onChanged={refresh} /> : <Explainer onNew={() => setCreating(true)} available={available} />}
      </Box>
      {creating && agent && (
        <NewRunDialog
          agent={agent}
          onClose={() => setCreating(false)}
          onStart={async (scenario) => {
            try {
              const run = await api.startRun(scenario);
              setCreating(false);
              refresh();
              onSelect(run.task_id);
            } catch (exc) {
              onError(exc instanceof Error ? exc.message : String(exc));
            }
          }}
        />
      )}
    </Box>
  );
}
