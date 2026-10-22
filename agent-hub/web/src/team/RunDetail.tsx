import AddRoundedIcon from '@mui/icons-material/AddRounded';
import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import CircularProgress from '@mui/material/CircularProgress';
import Collapse from '@mui/material/Collapse';
import FormControlLabel from '@mui/material/FormControlLabel';
import IconButton from '@mui/material/IconButton';
import LinearProgress from '@mui/material/LinearProgress';
import Switch from '@mui/material/Switch';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { alpha, useTheme } from '@mui/material/styles';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';
import { shortTask } from '../format';
import { MONO } from '../theme';
import type { RunDetail as Detail, TrajectoryEvent } from '../types';
import { Bullets, Card, DiffView, Field, Mono, PassIcon, Paths, RunChip, StatusChip, outcomeTone } from './parts';

type StepStatus = 'pending' | 'active' | 'done' | 'failed' | 'waiting' | 'skipped';

const STEPS = [
  { key: 'diagnose', label: 'Diagnose', who: 'Doctor' },
  { key: 'retrieve_context', label: 'Brief', who: 'Librarian' },
  { key: 'approval', label: 'Approve', who: 'You' },
  { key: 'patch', label: 'Patch', who: 'Mechanic' },
  { key: 'verify', label: 'Verify', who: 'Doctor' },
] as const;

function stepStatuses(run: Detail): Record<string, StepStatus> {
  const events = run.timeline;
  const statuses: Record<string, StepStatus> = {};
  for (const step of STEPS) {
    if (step.key === 'approval') {
      const decision = [...events].reverse().find((e) => e.event === 'approval_recorded');
      statuses.approval = decision ? (decision.approved ? 'done' : 'failed') : events.some((e) => e.event === 'awaiting_approval') ? 'waiting' : 'pending';
      continue;
    }
    const requests = events.filter((e) => e.event === 'specialist_request' && e.request_type === step.key);
    if (!requests.length) {
      statuses[step.key] = run.state === 'finished' ? 'skipped' : 'pending';
      continue;
    }
    const last = requests.at(-1)!;
    const result = events.find((e) => e.event === 'specialist_result' && e.request_type === step.key && e.seq > last.seq);
    statuses[step.key] = result ? (result.status === 'ok' ? 'done' : 'failed') : run.state === 'running' ? 'active' : 'failed';
  }
  return statuses;
}

function Stepper({ run }: { run: Detail }) {
  const theme = useTheme();
  const statuses = stepStatuses(run);
  const colour = (status: StepStatus) =>
    status === 'done' ? theme.palette.success.main
      : status === 'failed' ? theme.palette.error.main
        : status === 'active' ? theme.palette.info.main
          : status === 'waiting' ? theme.palette.warning.main
            : theme.palette.text.disabled;
  return (
    <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 1 }}>
      {STEPS.map((step, index) => {
        const status = statuses[step.key];
        const c = colour(status);
        return (
          <Box key={step.key} sx={{ position: 'relative', pt: 0.5 }}>
            <Box sx={{ height: 3, borderRadius: 2, bgcolor: status === 'pending' || status === 'skipped' ? 'border' : c, mb: 1.25, overflow: 'hidden' }}>
              {status === 'active' && <LinearProgress sx={{ height: 3, bgcolor: alpha(c, 0.25) }} />}
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
              <Box sx={{ width: 18, height: 18, borderRadius: '50%', display: 'grid', placeItems: 'center', bgcolor: alpha(c, 0.14), color: c, fontSize: '0.6875rem', fontWeight: 700, flexShrink: 0 }}>
                {status === 'done' ? <CheckRoundedIcon sx={{ fontSize: 13 }} /> : status === 'failed' ? <CloseRoundedIcon sx={{ fontSize: 13 }} /> : status === 'active' ? <CircularProgress size={10} thickness={6} sx={{ color: c }} /> : index + 1}
              </Box>
              <Typography variant="body2" sx={{ fontWeight: 600, color: status === 'pending' || status === 'skipped' ? 'text.disabled' : 'text.primary' }} noWrap>
                {step.label}
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ pl: 3.25, display: 'block' }} noWrap>
              {status === 'skipped' ? 'Not needed' : status === 'waiting' ? 'Waiting for you' : step.who}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}

function ApprovalPanel({ run, onDone }: { run: Detail; onDone: (detail: Detail) => void }) {
  const proposed = run.artifacts.approval?.allowed_paths ?? run.artifacts.brief?.relevant_source_files ?? [];
  const [paths, setPaths] = useState<string[]>(proposed);
  const [checked, setChecked] = useState<Set<string>>(new Set(proposed));
  const [extra, setExtra] = useState('');
  const [rationale, setRationale] = useState('');
  const [allowTests, setAllowTests] = useState(false);
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const decide = async (approved: boolean) => {
    setBusy(approved ? 'approve' : 'reject');
    setError(null);
    try {
      await api.approveRun(run.task_id, { paths: paths.filter((p) => checked.has(p)), rationale, allow_tests: allowTests, approved });
      onDone(await api.continueRun(run.task_id, remember && approved));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(null);
    }
  };
  const add = () => {
    const path = extra.trim();
    if (!path) return;
    setPaths((all) => (all.includes(path) ? all : [...all, path]));
    setChecked((all) => new Set(all).add(path));
    setExtra('');
  };

  return (
    <Card title="Your decision" aside={<StatusChip label="Needs approval" tone="warning" />}>
      <Typography variant="body2" color="text.secondary">
        The Mechanic may edit only the paths you approve, in the run's copy of config-service. The original is never touched.
      </Typography>
      <Field label="Edit boundary">
        <Box sx={{ display: 'grid' }}>
          {paths.map((path) => (
            <FormControlLabel
              key={path}
              control={
                <Checkbox
                  size="small"
                  checked={checked.has(path)}
                  onChange={(event) =>
                    setChecked((all) => {
                      const next = new Set(all);
                      if (event.target.checked) next.add(path);
                      else next.delete(path);
                      return next;
                    })
                  }
                />
              }
              label={<Box component="span" sx={{ fontFamily: MONO, fontSize: '0.78rem', wordBreak: 'break-all' }}>{path}</Box>}
            />
          ))}
          <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
            <TextField size="small" fullWidth placeholder="Add a workspace path, e.g. src/ConfigApi.Service/Middleware/" value={extra} onChange={(e) => setExtra(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && add()} slotProps={{ htmlInput: { style: { fontFamily: MONO, fontSize: '0.78rem' } } }} />
            <IconButton onClick={add} aria-label="Add path" disabled={!extra.trim()}>
              <AddRoundedIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      </Field>
      <TextField label="Rationale" required multiline minRows={2} value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="Why this boundary is right, or why you are rejecting it" />
      <Box sx={{ display: 'grid', gap: 0.5 }}>
        <FormControlLabel
          control={<Switch checked={allowTests} onChange={(e) => setAllowTests(e.target.checked)} />}
          label={
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 550 }}>Let the Mechanic run the tests</Typography>
              <Typography variant="caption" color="text.secondary">This runs the code it wrote. The Doctor verifies either way.</Typography>
            </Box>
          }
        />
        <FormControlLabel
          control={<Switch checked={remember} onChange={(e) => setRemember(e.target.checked)} />}
          label={
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 550 }}>Remember a verified repair</Typography>
              <Typography variant="caption" color="text.secondary">The Librarian writes a decision note citing this run's artifacts.</Typography>
            </Box>
          }
        />
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
        <Button color="inherit" variant="outlined" disabled={!!busy || !rationale.trim()} onClick={() => decide(false)} startIcon={busy === 'reject' ? <CircularProgress size={14} /> : <CloseRoundedIcon />}>
          Reject
        </Button>
        <Button variant="contained" disabled={!!busy || !rationale.trim() || checked.size === 0} onClick={() => decide(true)} startIcon={busy === 'approve' ? <CircularProgress size={14} color="inherit" /> : <CheckRoundedIcon />}>
          Approve and repair
        </Button>
      </Box>
    </Card>
  );
}

function describeEvent(e: TrajectoryEvent): string {
  switch (e.event) {
    case 'specialist_request':
      return `${e.agent} asked to ${String(e.request_type).replace(/_/g, ' ')}`;
    case 'specialist_result':
      return `${e.agent} ${e.status}: ${e.summary}${e.workspace_changed ? ' (changed the workspace)' : ''}`;
    case 'specialist_error':
      return `${e.agent} crashed: ${e.error}`;
    case 'artifact_written':
      return `Wrote ${String(e.path).split(/[\\/]/).pop()}`;
    case 'approval_proposed':
      return `Approval proposed for ${(e.allowed_paths as string[]).join(', ') || 'nothing'}`;
    case 'approval_recorded':
      return `${e.approved_by} ${e.approved ? 'approved' : 'rejected'} ${(e.allowed_paths as string[]).join(', ') || ''}`;
    case 'workflow_end':
      return `Finished: ${e.claim}`;
    default: {
      const { seq: _s, timestamp: _t, event, ...rest } = e;
      const detail = Object.entries(rest).map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`).join(', ');
      return `${event.replace(/_/g, ' ')}${detail ? ` (${detail})` : ''}`;
    }
  }
}

function Timeline({ events }: { events: TrajectoryEvent[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Card title={`Trajectory (${events.length} events)`} aside={<Button size="small" color="inherit" onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'}</Button>}>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ display: 'grid', gap: 0.25 }}>
          {events.map((e) => (
            <Box key={e.seq} sx={{ display: 'grid', gridTemplateColumns: '28px 70px 1fr', gap: 1, fontSize: '0.8rem', py: 0.4 }}>
              <Typography variant="caption" color="text.disabled" sx={{ fontFamily: MONO, textAlign: 'right' }}>{e.seq}</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: MONO }}>{e.timestamp.slice(11, 19)}</Typography>
              <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>{describeEvent(e)}</Typography>
            </Box>
          ))}
        </Box>
      </Collapse>
    </Card>
  );
}

export function RunDetail({ taskId, onChanged }: { taskId: string; onChanged: () => void }) {
  const [run, setRun] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [continuing, setContinuing] = useState(false);
  const shown = useRef(taskId);
  shown.current = taskId;
  const lastState = useRef<string | null>(null);

  const load = useCallback(async () => {
    try {
      const detail = await api.run(taskId);
      if (shown.current !== taskId) return;
      if (lastState.current && lastState.current !== detail.state) onChanged();
      lastState.current = detail.state;
      setRun(detail);
      setError(null);
    } catch (exc) {
      if (shown.current === taskId) setError(exc instanceof Error ? exc.message : String(exc));
    }
  }, [taskId, onChanged]);

  useEffect(() => {
    setRun(null);
    setError(null);
    lastState.current = null;
    load();
  }, [load]);

  // While a step runs, look again every two seconds; each load re-arms this.
  useEffect(() => {
    if (run?.state !== 'running') return;
    const timer = setTimeout(load, 2000);
    return () => clearTimeout(timer);
  }, [run, load]);

  if (error) return <Alert severity="error" sx={{ m: 3 }}>{error}</Alert>;
  if (!run) return <Box sx={{ display: 'grid', placeItems: 'center', py: 12 }}><CircularProgress size={26} /></Box>;

  const { diagnosis, brief, approval, patch, verification } = run.artifacts;
  const passedEvals = run.evals.filter((e) => e.passed).length;
  const update = (detail: Detail) => {
    lastState.current = detail.state;
    setRun(detail);
    onChanged();
  };

  return (
    <Box sx={{ maxWidth: 920, mx: 'auto', px: { xs: 2, sm: 3 }, py: 3, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr)', gap: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, flexWrap: 'wrap' }}>
        <Box sx={{ flex: 1, minWidth: 240 }}>
          <Typography variant="h5" component="h1">
            {run.scenario ? run.scenario.replace(/-/g, ' ') : 'Health check and repair'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
            {shortTask(run.task_id)} · <Box component="span" sx={{ fontFamily: MONO, fontSize: '0.75rem' }}>{run.task_id}</Box>
          </Typography>
        </Box>
        <RunChip run={run} />
      </Box>
      {run.scenario_description && (
        <Typography variant="body2" color="text.secondary">
          Seeded regression: {run.scenario_description}
        </Typography>
      )}

      <Stepper run={run} />

      {run.state === 'running' && (
        <Alert severity="info" icon={<CircularProgress size={18} />} sx={{ alignItems: 'center' }}>
          {run.step ? `${run.step.agent} is working: ${run.step.request_type.replace(/_/g, ' ')}.` : 'Starting...'} This page updates by itself.
        </Alert>
      )}
      {run.state === 'finished' && (
        <Alert severity={outcomeTone(run.outcome) === 'success' ? 'success' : outcomeTone(run.outcome) === 'warning' ? 'warning' : 'error'}>
          {run.claim}
        </Alert>
      )}
      {run.state === 'interrupted' && (
        <Alert severity="warning">This run's step was cut off when the hub stopped. Its artifacts are below; start a new run to repair.</Alert>
      )}
      {(run.state === 'approved' || run.state === 'rejected') && (
        <Alert
          severity="info"
          action={
            <Button
              size="small"
              variant="contained"
              disabled={continuing}
              startIcon={continuing ? <CircularProgress size={14} color="inherit" /> : <PlayArrowRoundedIcon />}
              onClick={async () => {
                setContinuing(true);
                try {
                  update(await api.continueRun(run.task_id, false));
                } catch (exc) {
                  setError(exc instanceof Error ? exc.message : String(exc));
                } finally {
                  setContinuing(false);
                }
              }}
            >
              Continue
            </Button>
          }
        >
          The decision is recorded. Continue to {run.state === 'approved' ? 'patch and verify' : 'close the run'}.
        </Alert>
      )}

      {run.state === 'awaiting_approval' && <ApprovalPanel run={run} onDone={update} />}

      {diagnosis && (
        <Card title="Diagnosis · Doctor" aside={<StatusChip label={diagnosis.status} tone={diagnosis.status === 'healthy' ? 'success' : diagnosis.status === 'unhealthy' ? 'error' : 'warning'} />}>
          {Object.keys(diagnosis.test_counts).length > 0 && (
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              {Object.entries(diagnosis.test_counts).map(([name, count]) => (
                <Box key={name}>
                  <Typography variant="h6" sx={{ fontVariantNumeric: 'tabular-nums', color: name === 'failed' && count > 0 ? 'error.main' : 'text.primary' }}>{count}</Typography>
                  <Typography variant="caption" color="text.secondary">{name}</Typography>
                </Box>
              ))}
            </Box>
          )}
          {diagnosis.failing_tests.length > 0 && <Field label="Failing tests"><Bullets items={diagnosis.failing_tests} mono /></Field>}
          {diagnosis.observed_error && <Field label="Observed error"><Mono>{diagnosis.observed_error}</Mono></Field>}
          <Field label="Suspected cause">{diagnosis.suspected_cause || 'None given'}</Field>
          <Field label="Relevant files"><Paths paths={diagnosis.relevant_files} /></Field>
          {diagnosis.uncertainty.length > 0 && <Field label="Uncertainty"><Bullets items={diagnosis.uncertainty} /></Field>}
          <Field label="Recommended next step">{diagnosis.recommended_next_step}</Field>
        </Card>
      )}

      {brief && (
        <Card title="Context brief · Librarian" aside={<Typography variant="caption" color="text.secondary">confidence {Math.round(brief.confidence * 100)}%</Typography>}>
          <Field label="Facts"><Bullets items={brief.facts} /></Field>
          <Field label="Suggested constraints"><Bullets items={brief.suggested_constraints} /></Field>
          <Field label="Source files"><Paths paths={brief.relevant_source_files} /></Field>
          <Field label="Tests"><Paths paths={brief.relevant_tests} /></Field>
          <Field label="Decision notes"><Paths paths={brief.relevant_memory_notes} /></Field>
          {brief.gaps.length > 0 && <Field label="Gaps"><Bullets items={brief.gaps} /></Field>}
        </Card>
      )}

      {approval && approval.approved_by !== 'proposal' && (
        <Card title="Approval" aside={<StatusChip label={approval.approved ? 'approved' : 'rejected'} tone={approval.approved ? 'success' : 'neutral'} />}>
          <Field label="Allowed paths"><Paths paths={approval.allowed_paths} /></Field>
          <Field label="Allowed commands"><Paths paths={approval.allowed_commands} /></Field>
          <Field label="Rationale">{approval.rationale}</Field>
        </Card>
      )}

      {patch && (
        <Card title="Patch · Mechanic" aside={<Typography variant="caption" color="text.secondary">{patch.mode}</Typography>}>
          <Field label="Intent">{patch.intent}</Field>
          <Field label="Files changed"><Paths paths={patch.files_changed} /></Field>
          <Field label="Rationale">{patch.rationale}</Field>
          {patch.risks.length > 0 && <Field label="Risks"><Bullets items={patch.risks} /></Field>}
        </Card>
      )}

      {run.diff && (
        <Card title={`Workspace diff · ${run.changed_files.length} file${run.changed_files.length === 1 ? '' : 's'}`}>
          <DiffView diff={run.diff} />
        </Card>
      )}

      {verification && (
        <Card title="Verification · Doctor" aside={<StatusChip label={verification.status} tone={verification.status === 'verified' ? 'success' : verification.status === 'failed' ? 'error' : 'warning'} />}>
          <Field label="Checks run"><Paths paths={verification.checks_run} /></Field>
          {verification.remaining_failures.length > 0 && <Field label="Remaining failures"><Bullets items={verification.remaining_failures} mono /></Field>}
          <Field label="Recommendation">{verification.recommendation}</Field>
        </Card>
      )}

      {run.evals.length > 0 && (
        <Card title="Coordination evals" aside={<StatusChip label={`${passedEvals}/${run.evals.length} passed`} tone={passedEvals === run.evals.length ? 'success' : 'error'} />}>
          <Box sx={{ display: 'grid', gap: 0.25 }}>
            {run.evals.map((e) => (
              <Box key={`${e.group}-${e.name}`} sx={{ display: 'grid', gridTemplateColumns: '20px 96px 1fr', gap: 1, alignItems: 'start', py: 0.5, borderBottom: 1, borderColor: 'border', '&:last-child': { borderBottom: 0 } }}>
                <Box sx={{ pt: 0.25 }}><PassIcon passed={e.passed} /></Box>
                <Typography variant="caption" color="text.secondary" sx={{ pt: 0.2 }}>{e.group}</Typography>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 550 }}>{e.name}</Typography>
                  <Typography variant="caption" color="text.secondary">{e.detail}</Typography>
                </Box>
              </Box>
            ))}
          </Box>
        </Card>
      )}

      <Timeline events={run.timeline} />
    </Box>
  );
}
