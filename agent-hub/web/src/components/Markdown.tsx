import CheckRoundedIcon from '@mui/icons-material/CheckRounded';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import Box from '@mui/material/Box';
import ButtonBase from '@mui/material/ButtonBase';
import { useTheme } from '@mui/material/styles';
import { memo, useState } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import { MONO } from '../theme';

type HastNode = { type: string; value?: string; children?: HastNode[]; properties?: { className?: unknown } };

function textOf(node: HastNode | undefined): string {
  if (!node) return '';
  if (node.type === 'text') return node.value ?? '';
  return (node.children ?? []).map(textOf).join('');
}

export function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <ButtonBase
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1600);
      }}
      sx={{
        gap: 0.5,
        px: 0.75,
        py: 0.25,
        borderRadius: 1.5,
        fontSize: '0.75rem',
        color: 'text.secondary',
        '&:hover': { color: 'text.primary', bgcolor: 'background.hover' },
      }}
    >
      {copied ? <CheckRoundedIcon sx={{ fontSize: 14 }} /> : <ContentCopyRoundedIcon sx={{ fontSize: 13 }} />}
      {copied ? 'Copied' : label}
    </ButtonBase>
  );
}

const components: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
  pre: ({ node, children }) => {
    const code = (node as HastNode | undefined)?.children?.[0];
    const classes = code?.properties?.className;
    const language = (Array.isArray(classes) ? classes : [])
      .map(String)
      .find((name) => name.startsWith('language-'))
      ?.slice('language-'.length);
    return (
      <Box className="code-block" sx={{ my: 1.75, border: 1, borderColor: 'border', borderRadius: 2.5, overflow: 'hidden', bgcolor: 'background.code' }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            pl: 1.75,
            pr: 0.75,
            py: 0.5,
            borderBottom: 1,
            borderColor: 'border',
            fontFamily: MONO,
            fontSize: '0.72rem',
            color: 'text.secondary',
          }}
        >
          <span>{language ?? 'text'}</span>
          <CopyButton text={textOf(code).replace(/\n$/, '')} />
        </Box>
        <pre>{children}</pre>
      </Box>
    );
  },
};

/** Syntax colours that read well on both themes' code background. */
function useCodeColours() {
  const dark = useTheme().palette.mode === 'dark';
  const c = dark
    ? { kw: '#c4a7ff', str: '#9ee6a8', num: '#ffb38a', fn: '#82b8ff', com: '#6f7480', type: '#ffd580', attr: '#7fd8e6', del: '#ff8f8f' }
    : { kw: '#7c3aed', str: '#15803d', num: '#c2410c', fn: '#1d4ed8', com: '#8a8f98', type: '#a16207', attr: '#0e7490', del: '#b91c1c' };
  return {
    '& .hljs-keyword, & .hljs-selector-tag, & .hljs-literal, & .hljs-built_in': { color: c.kw },
    '& .hljs-string, & .hljs-regexp, & .hljs-addition, & .hljs-template-string': { color: c.str },
    '& .hljs-number, & .hljs-symbol, & .hljs-bullet': { color: c.num },
    '& .hljs-title, & .hljs-title.function_, & .hljs-section': { color: c.fn },
    '& .hljs-comment, & .hljs-quote, & .hljs-meta': { color: c.com, fontStyle: 'italic' },
    '& .hljs-type, & .hljs-title.class_, & .hljs-class': { color: c.type },
    '& .hljs-attr, & .hljs-attribute, & .hljs-variable, & .hljs-property, & .hljs-params': { color: c.attr },
    '& .hljs-deletion': { color: c.del },
  };
}

function MarkdownView({ text }: { text: string }) {
  const colours = useCodeColours();
  return (
    <Box
      sx={{
        fontSize: '0.9375rem',
        lineHeight: 1.7,
        overflowWrap: 'anywhere',
        color: 'text.primary',
        '& > :first-child': { mt: 0 },
        '& > :last-child': { mb: 0 },
        '& p': { my: 1.25 },
        '& ul, & ol': { my: 1.25, pl: 3 },
        '& li': { my: 0.5, pl: 0.25 },
        '& li > p': { my: 0.5 },
        '& li::marker': { color: 'text.secondary' },
        '& h1, & h2, & h3, & h4': { mt: 3, mb: 1, lineHeight: 1.3, fontWeight: 650, letterSpacing: '-0.01em' },
        '& h1': { fontSize: '1.375rem' },
        '& h2': { fontSize: '1.2rem' },
        '& h3': { fontSize: '1.05rem' },
        '& h4': { fontSize: '0.95rem' },
        '& a': { color: 'primary.main', textDecoration: 'none', '&:hover': { textDecoration: 'underline' } },
        '& strong': { fontWeight: 650 },
        '& :not(pre) > code': {
          fontFamily: MONO,
          fontSize: '0.84em',
          bgcolor: 'background.code',
          border: 1,
          borderColor: 'border',
          px: 0.6,
          py: 0.15,
          borderRadius: 1.25,
        },
        '& pre': { m: 0, p: 1.75, overflowX: 'auto', fontFamily: MONO, fontSize: '0.8125rem', lineHeight: 1.6 },
        '& pre code': { fontFamily: 'inherit' },
        '& blockquote': { borderLeft: 3, borderColor: 'borderStrong', pl: 2, ml: 0, color: 'text.secondary' },
        '& table': {
          display: 'block',
          overflowX: 'auto',
          borderCollapse: 'separate',
          borderSpacing: 0,
          my: 1.75,
          fontSize: '0.875rem',
          border: 1,
          borderColor: 'border',
          borderRadius: 2,
        },
        '& th, & td': { borderBottom: 1, borderColor: 'border', px: 1.5, py: 0.9, textAlign: 'left', verticalAlign: 'top' },
        '& tr:last-of-type td': { borderBottom: 0 },
        '& th': { bgcolor: 'background.code', fontWeight: 600 },
        '& hr': { border: 0, borderTop: 1, borderColor: 'border', my: 2.5 },
        ...colours,
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[[rehypeHighlight, { detect: false }]]} components={components}>
        {text}
      </ReactMarkdown>
    </Box>
  );
}

export const Markdown = memo(MarkdownView);
